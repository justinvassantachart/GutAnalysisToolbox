import unittest
from run_workflows import classify

class ClassificationTests(unittest.TestCase):
    def test_all_pass(self):
        self.assertEqual(classify(0, [{"status":"PASS"}])[0], "PASS")
    def test_exit_failure_not_masked_by_success_report(self):
        self.assertEqual(classify(1, [{"status":"PASS"}])[0], "FAIL")
    def test_report_failure_not_masked_by_zero_exit(self):
        self.assertEqual(classify(0, [{"status":"FAIL"}])[0], "FAIL")
    def test_blocker_is_partial(self):
        self.assertEqual(classify(0, [{"status":"PASS"},{"status":"BLOCKED_ENVIRONMENT"}])[0], "PARTIAL")
    def test_unrun_is_partial(self):
        self.assertEqual(classify(0, [{"status":"NOT_RUN"}])[0], "PARTIAL")
    def test_empty_or_unknown_report_cannot_pass(self):
        for checks in ([],[{}],[{"status":"SKIPPED"}]):
            self.assertEqual(classify(0, checks)[0], "FAIL")

if __name__ == "__main__": unittest.main()
