import ij.IJ;
import ij.ImageJ;
import ij.Macro;
import ij.WindowManager;
import ij.measure.ResultsTable;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Actual IJ1 option parser and Results command, no model or production adapter. */
public final class LegacyMacroOptionProbe {
    public static void main(String[] args) throws Exception {
        Path output = Path.of(args[0]).toAbsolutePath();
        Path settings = Path.of(args[1]).toAbsolutePath();
        Files.createDirectories(output);
        Path original = output.resolve("GAT/Tools/commands/gat_settings.ijm");
        Path candidate = output.resolve("GAT MacroFork/Tools/commands/gat_settings [MacroFork].ijm");
        Files.createDirectories(original.getParent());
        Files.createDirectories(candidate.getParent());
        Files.copy(settings, original);
        Files.copy(settings, candidate);
        new ImageJ(ImageJ.NO_SHOW);
        StringBuilder rows = new StringBuilder();
        String reference = null;
        boolean passed = true;
        String[] names = {"original-unquoted", "candidate-unquoted-negative", "candidate-nested-brackets"};
        Path[] paths = {original, candidate, candidate};
        for (int i = 0; i < paths.length; i++) {
            String option = "open=" + (i == 2 ? "[" + paths[i] + "]" : paths[i]);
            String parsed = Macro.getValue(option, "open", "MISSING");
            IJ.getErrorMessage();
            IJ.redirectErrorMessages(true); // Record the expected Open Results error without a modal dialog.
            IJ.run("Results... ", option);
            String error = IJ.getErrorMessage();
            ResultsTable table = ResultsTable.getResultsTable("Results");
            String text = table == null ? null : table.getColumnHeadings() + "\n" + table.getRowAsString(0);
            boolean good;
            if (i == 0) {
                reference = text;
                good = parsed.equals(paths[i].toString()) && error == null && table != null && table.size() > 5;
            } else if (i == 1) {
                good = parsed.equals(candidate.toString().substring(0, candidate.toString().indexOf(' ')))
                    && error != null && error.startsWith("Error opening ") && table == null;
            } else good = parsed.equals(candidate.toString()) && error == null && reference != null && reference.equals(text);
            passed &= good;
            if (i > 0) rows.append(",\n");
            rows.append("{\"case\":").append(q(names[i])).append(",\"option\":").append(q(option))
                .append(",\"parsed\":").append(q(parsed)).append(",\"error\":").append(q(error))
                .append(",\"table_rows\":").append(table == null ? 0 : table.size())
                .append(",\"table_first_row\":").append(q(text)).append(",\"pass\":").append(good).append('}');
            if (WindowManager.getWindow("Results") != null) IJ.run("Close");
        }
        String report = "{\"schema_version\":1,\"scope\":\"actual-IJ1-option-parser-and-Results-command-only\",\"ij_version\":"
            + q(IJ.getVersion()) + ",\"status\":" + q(passed ? "PASS_OPTIONS_CONTROL" : "FAIL_OPTIONS_CONTROL")
            + ",\"cases\":[\n" + rows + "\n]}\n";
        Files.writeString(output.resolve("report.json"), report, StandardCharsets.UTF_8);
        System.out.println(report);
        System.exit(passed ? 0 : 2);
    }
    private static String q(String s) {
        return s == null ? "null" : "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"")
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }
}
