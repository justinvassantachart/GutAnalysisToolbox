package org.gatanalysis.inference;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** Extracts to a private temporary directory and never fetches files or follows archive links. */
final class ModelArchive implements AutoCloseable {
    static final long MAX_UNCOMPRESSED_BYTES = 1L << 30;
    static final int MAX_ENTRIES = 20_000;
    final Path root;
    final Path modelDirectory;

    private ModelArchive(Path root, Path modelDirectory) {
        this.root = root;
        this.modelDirectory = modelDirectory;
    }

    static ModelArchive extract(Path archive) throws IOException {
        if (!Files.isRegularFile(archive)) throw new IOException("Model ZIP not found: " + archive);
        Path root = Files.createTempDirectory("gat-saved-model-");
        try {
            long total = 0;
            int count = 0;
            List<Path> savedModels = new ArrayList<>();
            byte[] buffer = new byte[64 * 1024];
            try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(Files.newInputStream(archive)))) {
                ZipEntry entry;
                while ((entry = zip.getNextEntry()) != null) {
                    if (++count > MAX_ENTRIES) throw new IOException("Too many files in model archive");
                    String name = entry.getName();
                    // ZIPs use '/', so reject backslashes and Windows drive names on every OS.
                    if (name.isEmpty() || name.indexOf('\\') >= 0 || name.indexOf(':') >= 0)
                        throw new IOException("Unsafe model ZIP entry: " + name);
                    Path target = root.resolve(name).normalize();
                    if (!target.startsWith(root) || target.equals(root))
                        throw new IOException("Model ZIP entry escapes extraction directory: " + name);
                    if (entry.isDirectory()) {
                        Files.createDirectories(target);
                    } else {
                        Files.createDirectories(target.getParent());
                        try (OutputStream out = Files.newOutputStream(target, StandardOpenOption.CREATE_NEW)) {
                            int n;
                            while ((n = zip.read(buffer)) != -1) {
                                total += n;
                                if (total > MAX_UNCOMPRESSED_BYTES)
                                    throw new IOException("Model ZIP exceeds 1 GiB uncompressed limit");
                                out.write(buffer, 0, n);
                            }
                        }
                        if (target.getFileName().toString().equals("saved_model.pb")) {
                            if (Files.size(target) == 0) throw new IOException("Empty saved_model.pb");
                            savedModels.add(target.getParent());
                        }
                    }
                    zip.closeEntry();
                }
            }
            if (savedModels.size() != 1)
                throw new IOException("Expected exactly one saved_model.pb in model ZIP, found " + savedModels.size());
            return new ModelArchive(root, savedModels.get(0));
        } catch (Throwable failure) {
            try { removeTree(root); } catch (IOException cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    @Override public void close() throws IOException { removeTree(root); }

    private static void removeTree(Path root) throws IOException {
        if (!Files.exists(root)) return;
        List<Path> paths;
        try (Stream<Path> walk = Files.walk(root)) {
            paths = walk.sorted(Comparator.reverseOrder()).collect(Collectors.toList());
        }
        IOException failure = null;
        for (Path path : paths) {
            try { Files.deleteIfExists(path); }
            catch (IOException e) { if (failure == null) failure = e; else failure.addSuppressed(e); }
        }
        if (failure != null) throw failure;
    }
}
