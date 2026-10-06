import importlib.util
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("multiplex_runner", HERE / "run.py")
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


class ReportingTests(unittest.TestCase):
    def checks(self, case="full-sift"):
        return [{"id": name, "status": "PASS"} for name in RUN.REQUIRED[case]]

    def test_empty_report_is_not_pass(self):
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, [])[0], "FAIL_REPORT")

    def test_setup_timeout_is_blocker(self):
        result = {"exit_code": -9, "resource_stop_reason": "process deadline exceeded"}
        self.assertEqual(RUN.classify("full-sift", result, [], "display_setup")[0], "BLOCKED_SETUP")

    def test_runtime_timeout_is_not_algorithm_failure(self):
        result = {"exit_code": -9, "resource_stop_reason": "process deadline exceeded"}
        self.assertEqual(RUN.classify("full-sift", result, [], "service_run")[0], "INCONCLUSIVE_RESOURCE_LIMIT")

    def test_unknown_dialog_is_not_autoaccepted_or_called_algorithm_failure(self):
        result = {"exit_code": -9, "resource_stop_reason": "process deadline exceeded"}
        self.assertEqual(RUN.classify("full-sift", result, [], "service_run", "DIALOG_UNHANDLED title=unexpected")[0], "BLOCKED_INTERACTION")

    def test_reached_assertion_failure_survives_later_timeout(self):
        result = {"exit_code": -9, "resource_stop_reason": "process deadline exceeded"}
        self.assertEqual(RUN.classify("full-sift", result, [{"id": "saved_calibration", "status": "FAIL"}], "output_assertions")[0], "FAIL_ASSERTION")

    def test_required_check_cannot_be_omitted(self):
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, self.checks()[:-1])[0], "FAIL_REPORT")

    def test_unknown_status_cannot_pass(self):
        checks = self.checks(); checks[0]["status"] = "UNKNOWN"
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, checks)[0], "FAIL_REPORT")

    def test_explicit_limits_do_not_impersonate_tested_scopes(self):
        checks = self.checks() + [{"id": name, "status": "NOT_RUN"} for name in RUN.LIMITS["full-sift"]]
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, checks)[0], "PASS")
        checks.append({"id": "unanticipated_missing_work", "status": "NOT_RUN"})
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, checks)[0], "FAIL_REPORT")

    def test_duplicate_id_fails(self):
        checks = self.checks(); checks.append(checks[0])
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 0}, checks)[0], "FAIL_REPORT")

    def test_nonzero_exit_is_not_pass(self):
        self.assertEqual(RUN.classify("full-sift", {"exit_code": 1}, self.checks())[0], "FAIL_PROCESS")

    def test_native_dependency_pins_match_existing_workflows(self):
        canonical = {a["filename"]: a for a in json.loads((HERE.parent / "workflows/dependencies.json").read_text())["artifacts"]}
        for artifact in json.loads((HERE / "dependencies.json").read_text())["artifacts"]:
            self.assertEqual(artifact, canonical[artifact["filename"]])

    def test_common_pattern_is_unchanged(self):
        def body(text, signature):
            start = text.index(signature); brace = text.index("{", start); depth = 1; end = brace + 1
            while depth:
                depth += (text[end] == "{") - (text[end] == "}"); end += 1
            return re.sub(r"\s+", "", text[brace:end])
        original = (HERE.parent / "workflows/RegistrationMorphologySmoke.java").read_text()
        current = (HERE / "MultiplexFullProbe.java").read_text()
        for signature in ("ByteProcessor pattern()", "void rectangle(", "ByteProcessor translated("):
            self.assertEqual(body(original, signature), body(current, signature))

    def test_official_command_mapping_rejects_substitutes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "plugin.jar"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("plugins.config", 'Plugins>Transform, "Landmark Correspondences", FakePlugin\n')
            with self.assertRaisesRegex(ValueError, "mapping differs"):
                RUN.verify_official_commands(path, {"Landmark Correspondences": "Transform_Roi"})


if __name__ == "__main__":
    unittest.main()
