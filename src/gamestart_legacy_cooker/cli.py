from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .archive import (
    METHOD_ZLIB,
    ArchiveEntry,
    ArchiveFormatError,
    filter_entries,
    pack_directory,
    scan_archive,
    unpack_archive,
)


def _size(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def _ratio(entry: ArchiveEntry) -> str:
    if entry.length == 0:
        return "0%"
    return f"{entry.stored_length * 100 / entry.length:.1f}%"


def cmd_info(args: argparse.Namespace) -> int:
    info = scan_archive(args.archive, encoding=args.encoding)
    print(f"Archive: {info.path}")
    print(f"Revision: {info.revision}")
    print(f"Offset padding: {info.offset_padding}")
    print(f"Size padding: {info.size_padding}")
    print(f"Entries: {len(info.entries)}")
    print(f"Original data: {_size(info.original_size)}")
    print(f"Stored data: {_size(info.stored_size)}")
    print(f"File size: {_size(info.file_size)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    info = scan_archive(args.archive, encoding=args.encoding)
    entries = filter_entries(info.entries, args.include)

    if args.json:
        print(
            json.dumps(
                {
                    "archive": str(info.path),
                    "revision": info.revision,
                    "offset_padding": info.offset_padding,
                    "size_padding": info.size_padding,
                    "file_size": info.file_size,
                    "entries": [
                        {
                            "alias": entry.alias,
                            "method": entry.method_name,
                            "offset": entry.data_offset,
                            "length": entry.length,
                            "compressed_length": entry.compressed_length,
                            "stored_length": entry.stored_length,
                        }
                        for entry in entries
                    ],
                },
                indent=2,
            )
        )
        return 0

    if not args.names_only:
        print(f"{'method':<6} {'size':>12} {'stored':>12} {'ratio':>8} {'offset':>12} path")
    for entry in entries:
        if args.names_only:
            print(entry.alias)
        else:
            print(
                f"{entry.method_name:<6} "
                f"{entry.length:>12} "
                f"{entry.stored_length:>12} "
                f"{_ratio(entry):>8} "
                f"{entry.data_offset:>12} "
                f"{entry.alias}"
            )
    return 0


def cmd_unpack(args: argparse.Namespace) -> int:
    result = unpack_archive(
        args.archive,
        args.output_dir,
        overwrite=args.overwrite,
        encoding=args.encoding,
        include=args.include,
    )
    print(f"Unpacked {len(result.written)} file(s) to {result.output_dir}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    result = pack_directory(
        args.input_dir,
        args.archive,
        compression_level=args.compression,
        offset_padding=args.offset_padding,
        size_padding=args.size_padding,
        legacy=args.legacy,
        overwrite=args.overwrite,
        encoding=args.encoding,
        excludes=args.exclude,
        raw_patterns=args.raw,
        allow_empty=args.allow_empty,
    )
    print(f"Packed {len(result.entries)} file(s) into {result.archive}")
    if result.skipped_empty:
        print(f"Skipped {len(result.skipped_empty)} empty file(s). Use --allow-empty to store them.")
    if result.skipped_symlink:
        print(f"Skipped {len(result.skipped_symlink)} symlink(s).")
    if result.skipped_excluded:
        print(f"Skipped {len(result.skipped_excluded)} excluded file(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gamestart-cooker",
        description="Pack, list, and unpack legacy GameStart nArchive files (.nac/.gsa).",
    )
    parser.add_argument("--encoding", default="utf-8", help="Archive path encoding. Default: utf-8.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    info = subparsers.add_parser("info", help="Show archive metadata and aggregate sizes.")
    info.add_argument("archive", type=Path)
    info.set_defaults(func=cmd_info)

    list_parser = subparsers.add_parser("list", help="List archive entries.")
    list_parser.add_argument("archive", type=Path)
    list_parser.add_argument("--json", action="store_true", help="Emit JSON.")
    list_parser.add_argument("-n", "--names-only", action="store_true", help="Print only entry aliases.")
    list_parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Only show entries matching this glob. Can be repeated.",
    )
    list_parser.set_defaults(func=cmd_list)

    unpack = subparsers.add_parser("unpack", help="Extract an archive to a directory.")
    unpack.add_argument("archive", type=Path)
    unpack.add_argument("output_dir", type=Path)
    unpack.add_argument("-f", "--overwrite", action="store_true", help="Overwrite existing files.")
    unpack.add_argument(
        "--include",
        action="append",
        default=[],
        help="Only extract entries matching this glob. Can be repeated.",
    )
    unpack.set_defaults(func=cmd_unpack)

    pack = subparsers.add_parser("pack", help="Create an archive from a directory tree.")
    pack.add_argument("input_dir", type=Path)
    pack.add_argument("archive", type=Path)
    pack.add_argument(
        "-c",
        "--compression",
        type=int,
        default=6,
        help="Zlib level 0..9, or -1 for raw storage. Default: 6.",
    )
    pack.add_argument(
        "--offset-padding",
        type=int,
        default=4,
        help="Field/data alignment for enhanced archives. Default: 4.",
    )
    pack.add_argument(
        "--size-padding",
        type=int,
        default=0,
        help="Final archive size padding for enhanced archives. Default: 0.",
    )
    pack.add_argument("--legacy", action="store_true", help="Write the older NARC/CRAN header.")
    pack.add_argument("-f", "--overwrite", action="store_true", help="Overwrite the output archive.")
    pack.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip input aliases matching this glob. Can be repeated.",
    )
    pack.add_argument(
        "--raw",
        action="append",
        default=[],
        help="Store matching input aliases without zlib compression. Can be repeated.",
    )
    pack.add_argument(
        "--allow-empty",
        action="store_true",
        help="Store empty files. The original engine writer skipped them.",
    )
    pack.set_defaults(func=cmd_pack)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ArchiveFormatError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
