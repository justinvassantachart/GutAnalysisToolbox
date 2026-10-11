package services.merge;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Predicate;
import java.util.stream.Stream;
import java.util.stream.Collectors;
import java.nio.file.StandardOpenOption;

/**
 * Streams many delimited text files (typically CSV) into one or more merged outputs.
 *
 * Features
 * - Adds an "Experiment" column as the first column; its value is derived by a LabelStrategy.
 * - Writes the header only once per output, taken from the first matching file.
 * - Single-pattern mode: match files whose names contain a substring (case-insensitive).
 * - Multi-merge mode: discover base names (e.g., "results") in the first subfolder and
 *   merge each base across the entire tree as <base>.<ext>.
 * - Extension-aware APIs using FileExtension (default CSV).
 *
 * Notes
 * - CSV records are copied without changing their field delimiters, including quoted newlines.
 * - Empty lines are skipped.
 */
public class CsvMerger {

    private static final char BOM = '\uFEFF';

    private final LabelStrategy labelStrategy;
    private final Charset charset;
    private final boolean quoteLabelIfComma;
    private final boolean verifyHeaderMatch;

    /**
     * Construct with defaults:
     * charset = UTF-8, quoteLabelIfComma = true, verifyHeaderMatch = false
     */
    public CsvMerger(LabelStrategy labelStrategy) {
        this(labelStrategy, StandardCharsets.UTF_8, true, false);
    }

    public CsvMerger(LabelStrategy labelStrategy,
                     Charset charset,
                     boolean quoteLabelIfComma,
                     boolean verifyHeaderMatch) {
        this.labelStrategy = Objects.requireNonNull(labelStrategy, "labelStrategy");
        this.charset = Objects.requireNonNull(charset, "charset");
        this.quoteLabelIfComma = quoteLabelIfComma;
        this.verifyHeaderMatch = verifyHeaderMatch;
    }

    /* -------------------------------------------------------------
     * Public API — Single-pattern
     * ------------------------------------------------------------- */

    /** Back-compat: defaults to CSV extension. */
    public Path mergeSinglePattern(Path root, String namePattern) throws IOException, MergeException {
        return mergeSinglePattern(root, namePattern, FileExtension.CSV);
    }

    /**
     * Merge all files under {@code root} whose filename (case-insensitive)
     * contains {@code namePattern} and ends with {@code ext}.
     *
     * Output path: root/Merged_<experiment>_<sanitizedPattern>.<ext>
     */
    public Path mergeSinglePattern(Path root, String namePattern, FileExtension ext)
            throws IOException, MergeException {

        Objects.requireNonNull(root, "root");
        Objects.requireNonNull(namePattern, "namePattern");
        Objects.requireNonNull(ext, "ext");

        if (!Files.isDirectory(root)) {
            throw new MergeException("Root is not a directory: " + root);
        }

        final String experiment = root.getFileName().toString();
        final String sanitized = namePattern.replaceAll("\\W+", "_");
        final Path out = root.resolve("Merged_" + experiment + "_" + sanitized + "." + ext.ext());

        if (Files.exists(out)) {
            throw new MergeException("Output already exists: " + out);
        }

        final String needle = namePattern.toLowerCase(Locale.ROOT);

        Predicate<Path> match = p -> Files.isRegularFile(p)
                && ext.matches(p)
                && p.getFileName().toString().toLowerCase(Locale.ROOT).contains(needle);

        return writeMerged(root, out, match);
    }

    /* -------------------------------------------------------------
     * Public API — Multi from first subfolder (discover bases)
     * ------------------------------------------------------------- */

    /** Back-compat: defaults to CSV extension. */
    public List<Path> mergeFromFirstSubfolderPatterns(Path root) throws IOException, MergeException {
        return mergeFromFirstSubfolderPatterns(root, FileExtension.CSV);
    }

    /**
     * Discover unique base names for files with {@code ext} inside the first subdirectory of {@code root},
     * then for each base name B merge every matching {@code B.ext} across the entire tree under {@code root}.
     *
     * Output paths: root/Merged_<experiment>_<base>.<ext> for each discovered base.
     */
    public List<Path> mergeFromFirstSubfolderPatterns(Path root, FileExtension ext)
            throws IOException, MergeException {

        Objects.requireNonNull(root, "root");
        Objects.requireNonNull(ext, "ext");

        if (!Files.isDirectory(root)) {
            throw new MergeException("Root is not a directory: " + root);
        }

        Path first = DirectoryUtils.firstSubdirectory(root)
                .orElseThrow(() -> new MergeException("No subdirectories under: " + root));

        Set<String> bases = DirectoryUtils.collectBaseNames(first, ext);
        if (bases.isEmpty()) {
            throw new MergeException("No *." + ext.ext() + " files found under: " + first);
        }

        final String experiment = root.getFileName().toString();
        final List<Path> outs = new ArrayList<>(bases.size());

        // Preflight: ensure we won't overwrite any output
        for (String base : bases) {
            Path out = root.resolve("Merged_" + experiment + "_" + base + "." + ext.ext());
            if (Files.exists(out)) {
                throw new MergeException("Output already exists: " + out);
            }
        }

        // Write each merged output
        for (String base : bases) {
            final String exactFilename = ext.withExt(base);
            final Path out = root.resolve("Merged_" + experiment + "_" + base + "." + ext.ext());

            Predicate<Path> match = p -> Files.isRegularFile(p)
                    && ext.matches(p)
                    && p.getFileName().toString().equalsIgnoreCase(exactFilename);

            writeMerged(root, out, match);
            outs.add(out);
        }

        return outs;
    }

    /* -------------------------------------------------------------
     * Core writer
     * ------------------------------------------------------------- */

    /**
     * Walks {@code root}, filters with {@code fileMatch}, and writes a single merged output to {@code out}.
     * Adds the "Experiment" header and per-row label via {@link LabelStrategy}.
     *
     * IMPORTANT: iterates the stream with an iterator so checked MergeException can propagate.
     */
    private Path writeMerged(Path root, Path out, Predicate<Path> fileMatch)
            throws IOException, MergeException {

        final String[] headerHolder = { null };
        // Snapshot before creating output: otherwise its pattern-matching name
        // can be read while it is being written and recursively duplicate rows.
        final List<Path> inputs;
        try (Stream<Path> paths = Files.walk(root)) {
            inputs = paths.filter(fileMatch)
                    .filter(p -> !p.toAbsolutePath().normalize().equals(out.toAbsolutePath().normalize()))
                    .sorted().collect(Collectors.toList());
        } catch (UncheckedIOException error) { throw error.getCause(); }
        if (inputs.isEmpty()) throw new MergeException("No matching files found under: " + root);
        boolean created = false;
        try {
            BufferedWriter opened = Files.newBufferedWriter(out, charset, StandardOpenOption.CREATE_NEW);
            created = true;
            try (BufferedWriter writer = opened) {
                for (Path input : inputs) appendCsvFile(root, input, headerHolder, writer);
                if (headerHolder[0] == null) throw new MergeException("Matching files contain no CSV header: " + root);
            }
        } catch (IOException | MergeException | RuntimeException error) {
            if (created) {
                try { Files.deleteIfExists(out); }
                catch (IOException cleanup) { error.addSuppressed(cleanup); }
            }
            throw error;
        }
        return out;
    }

    /**
     * Appends one file into the merged writer.
     * - First non-empty line is treated as the header.
     * - Writes "Experiment,<header>" once (on the first file).
     * - Writes "<label>,<row>" for each subsequent line.
     */
    protected void appendCsvFile(Path root, Path csvFile, String[] headerHolder, BufferedWriter writer)
            throws IOException, MergeException {

        final String labelRaw = labelStrategy.labelFor(root, csvFile);
        final String label = formatLabel(labelRaw);

        try (BufferedReader br = Files.newBufferedReader(csvFile, charset)) {
            String line;
            boolean firstLine = true;

            while ((line = readRecord(br, csvFile)) != null) {
                if (line.isEmpty()) continue;

                // Strip UTF-8 BOM if it's at the start of the line
                if (firstLine && !line.isEmpty() && line.charAt(0) == BOM) {
                    line = line.substring(1);
                }

                if (firstLine) {
                    firstLine = false;

                    // Header handling
                    if (headerHolder[0] == null) {
                        headerHolder[0] = line;
                        writer.write("Experiment," + line);
                        writer.newLine();
                    } else if (verifyHeaderMatch && !line.equals(headerHolder[0])) {
                        throw new MergeException("Header mismatch in file: " + csvFile
                                + "\nExpected: " + headerHolder[0]
                                + "\nFound:    " + line);
                    }

                    continue; // do not treat header as data
                }

                // Data row
                writer.write(label);
                writer.write(',');
                writer.write(line);
                writer.newLine();
            }
        }
    }

    /** Keep one experiment label per logical record, including quoted line breaks. */
    private static String readRecord(BufferedReader reader, Path source) throws IOException, MergeException {
        String line = reader.readLine();
        if (line == null) return null;
        StringBuilder record = new StringBuilder(line);
        boolean quoted = false;
        while (true) {
            for (int i = 0; i < line.length(); i++) {
                if (line.charAt(i) != '"') continue;
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') i++;
                else quoted = !quoted;
            }
            if (!quoted) return record.toString();
            line = reader.readLine();
            if (line == null) throw new MergeException("Unclosed quoted CSV field in: " + source);
            record.append('\n').append(line);
        }
    }

    /* -------------------------------------------------------------
     * Helpers
     * ------------------------------------------------------------- */

    private String formatLabel(String raw) {
        if (raw == null) return "";
        String s = raw;
        if (quoteLabelIfComma && (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\n') >= 0 || s.indexOf('\r') >= 0)) {
            // CSV quoting: wrap in quotes and escape internal quotes by doubling them
            s = s.replace("\"", "\"\"");
            s = "\"" + s + "\"";
        }
        return s;
    }
}
