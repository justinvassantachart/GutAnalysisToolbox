import hashlib
from pathlib import Path
import tempfile
import unittest

from run_corpus import verify_input


class InputIntegrityTests(unittest.TestCase):
    def test_changed_input_is_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.bin"
            path.write_bytes(b"original")
            row = {"case_id": "test", "input_path": str(path),
                   "input_sha256": hashlib.sha256(b"original").hexdigest()}
            verify_input(row)
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum changed"):
                verify_input(row)


if __name__ == "__main__":
    unittest.main()
