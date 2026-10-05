from pathlib import Path
import tempfile
import unittest

from package_results import digest, partition, write_archive


class ArchiveTests(unittest.TestCase):
    def test_archives_are_deterministic_and_partitioned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for name in ("b.gz", "a.gz", "c.gz"):
                path = root / name
                path.write_bytes(name.encode() * 100)
                entries.append(("core/outlines/" + name, path))
            chunks = partition(entries, maximum=1200)
            self.assertGreater(len(chunks), 1)
            one, two = root / "one.zip", root / "two.zip"
            write_archive(one, entries)
            write_archive(two, list(reversed(entries)))
            self.assertEqual(digest(one), digest(two))

    def test_oversized_single_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.gz"
            path.write_bytes(b"x" * 2000)
            with self.assertRaisesRegex(ValueError, "exceeds archive budget"):
                partition([("large.gz", path)], maximum=1000)


if __name__ == "__main__":
    unittest.main()
