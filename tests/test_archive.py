import tempfile
import unittest
from pathlib import Path

from gamestart_legacy_cooker.archive import (
    ArchiveFormatError,
    compare_trees,
    pack_directory,
    safe_output_path,
    scan_archive,
    unpack_archive,
)


class ArchiveTests(unittest.TestCase):
    def test_pack_unpack_enhanced_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "hello.txt").write_text("hello GameStart\n", encoding="utf-8")
            (source / "data").mkdir()
            (source / "data" / "bytes.bin").write_bytes(bytes(range(256)))

            archive = root / "test.nac"
            packed = pack_directory(
                source,
                archive,
                compression_level=6,
                offset_padding=4,
                raw_patterns=("data/*",),
            )
            self.assertEqual(len(packed.entries), 2)

            info = scan_archive(archive)
            self.assertEqual(info.revision, "EnhancedLegacy")
            self.assertEqual(info.offset_padding, 4)
            self.assertEqual(len(info.entries), 2)
            methods = {entry.alias: entry.method_name for entry in info.entries}
            self.assertEqual(methods["data/bytes.bin"], "Raw")
            self.assertEqual(methods["hello.txt"], "Zlib")

            output = root / "output"
            unpack_archive(archive, output)
            self.assertEqual(compare_trees(source, output), [])

    def test_pack_unpack_legacy_raw_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "raw.txt").write_text("raw\n", encoding="utf-8")

            archive = root / "legacy.nac"
            pack_directory(source, archive, compression_level=-1, legacy=True)

            info = scan_archive(archive)
            self.assertEqual(info.revision, "Legacy")
            self.assertEqual(info.entries[0].method_name, "Raw")

            output = root / "output"
            unpack_archive(archive, output)
            self.assertEqual((output / "raw.txt").read_text(encoding="utf-8"), "raw\n")

    def test_safe_output_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ArchiveFormatError):
                safe_output_path(Path(tmp), "../escape.txt")


if __name__ == "__main__":
    unittest.main()
