from __future__ import annotations

import fnmatch
import os
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Iterable, List, Optional, Sequence


MAGIC_ENHANCED = 0x4E415244  # Commented as "NARD" in the engine, bytes are "DRAN".
MAGIC_LEGACY = 0x4E415243  # Commented as "NARC" in the engine, bytes are "CRAN".

REVISION_ENHANCED = "EnhancedLegacy"
REVISION_LEGACY = "Legacy"

METHOD_RAW = 0
METHOD_ZLIB = 1

MAX_ALIAS_LENGTH = 511


class ArchiveFormatError(RuntimeError):
    """Raised when a GameStart archive cannot be parsed safely."""


@dataclass(frozen=True)
class ArchiveEntry:
    alias: str
    method: int
    length: int
    compressed_length: int
    data_offset: int

    @property
    def stored_length(self) -> int:
        return self.compressed_length if self.method == METHOD_ZLIB else self.length

    @property
    def method_name(self) -> str:
        return "Zlib" if self.method == METHOD_ZLIB else "Raw"


@dataclass(frozen=True)
class ArchiveInfo:
    path: Path
    revision: str
    offset_padding: int
    size_padding: int
    file_size: int
    entries: List[ArchiveEntry] = field(default_factory=list)

    @property
    def original_size(self) -> int:
        return sum(entry.length for entry in self.entries)

    @property
    def stored_size(self) -> int:
        return sum(entry.stored_length for entry in self.entries)


@dataclass(frozen=True)
class PackResult:
    archive: Path
    entries: List[ArchiveEntry]
    skipped_empty: List[Path]
    skipped_symlink: List[Path]
    skipped_excluded: List[Path]


@dataclass(frozen=True)
class UnpackResult:
    archive: Path
    output_dir: Path
    entries: List[ArchiveEntry]
    written: List[Path]


def _read_exact(handle: BinaryIO, length: int, context: str) -> bytes:
    data = handle.read(length)
    if len(data) != length:
        raise ArchiveFormatError(f"Unexpected end of file while reading {context}.")
    return data


def _read_u32(handle: BinaryIO, context: str) -> int:
    return struct.unpack("<I", _read_exact(handle, 4, context))[0]


def _write_u32(handle: BinaryIO, value: int) -> None:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ArchiveFormatError(f"Value does not fit in a 32-bit unsigned field: {value}")
    handle.write(struct.pack("<I", value))


def align_position(position: int, padding: int) -> int:
    if padding <= 0:
        return position
    error = position % padding
    return position if error == 0 else position + padding - error


def _align_read(handle: BinaryIO, padding: int) -> None:
    target = align_position(handle.tell(), padding)
    if target != handle.tell():
        handle.seek(target)


def _align_write(handle: BinaryIO, padding: int) -> None:
    target = align_position(handle.tell(), padding)
    gap = target - handle.tell()
    if gap:
        handle.write(b"\x00" * gap)


def _decode_alias(alias_bytes: bytes, encoding: str) -> str:
    return alias_bytes.decode(encoding, errors="surrogateescape").replace("\\", "/")


def _encode_alias(alias: str, encoding: str) -> bytes:
    alias_bytes = alias.encode(encoding, errors="surrogateescape")
    if len(alias_bytes) > MAX_ALIAS_LENGTH:
        raise ArchiveFormatError(
            f"Archive alias is {len(alias_bytes)} bytes, maximum is {MAX_ALIAS_LENGTH}: {alias}"
        )
    return alias_bytes


def scan_archive(path: os.PathLike[str] | str, encoding: str = "utf-8") -> ArchiveInfo:
    archive_path = Path(path)
    file_size = archive_path.stat().st_size
    entries: List[ArchiveEntry] = []

    with archive_path.open("rb") as handle:
        magic = _read_u32(handle, "archive magic")
        if magic == MAGIC_ENHANCED:
            revision = REVISION_ENHANCED
            offset_padding = _read_u32(handle, "offset padding")
            size_padding = _read_u32(handle, "size padding")
        elif magic == MAGIC_LEGACY:
            revision = REVISION_LEGACY
            offset_padding = 0
            size_padding = 0
        else:
            raw_magic = struct.pack("<I", magic)
            raise ArchiveFormatError(
                f"Invalid GameStart archive magic {raw_magic!r} ({magic:#010x})."
            )

        while handle.tell() < file_size:
            # nArchive::Close writes the 0xffffffff EOF marker without first
            # applying offset padding. Check the current cursor before aligning
            # so old archives with an unaligned final marker still parse cleanly.
            unaligned_pos = handle.tell()
            marker = handle.read(4)
            if marker == b"\xff\xff\xff\xff":
                break
            handle.seek(unaligned_pos)

            _align_read(handle, offset_padding)
            if handle.tell() >= file_size:
                break

            header = handle.read(4)
            if not header:
                break
            if len(header) != 4:
                if all(byte == 0xFF for byte in header):
                    break
                raise ArchiveFormatError("Truncated entry name length.")

            alias_length = struct.unpack("<I", header)[0]
            if alias_length > MAX_ALIAS_LENGTH:
                break

            _align_read(handle, offset_padding)
            alias_bytes = _read_exact(handle, alias_length, "entry alias")
            alias = _decode_alias(alias_bytes, encoding)

            _align_read(handle, offset_padding)
            method = _read_exact(handle, 1, f"{alias} method")[0] & 1

            _align_read(handle, offset_padding)
            length = _read_u32(handle, f"{alias} original length")

            if method == METHOD_ZLIB:
                _align_read(handle, offset_padding)
                compressed_length = _read_u32(handle, f"{alias} compressed length")
            else:
                compressed_length = length

            _align_read(handle, offset_padding)
            data_offset = handle.tell()
            data_end = data_offset + compressed_length
            if data_end > file_size:
                raise ArchiveFormatError(
                    f"Entry {alias!r} extends beyond the archive end "
                    f"({data_end} > {file_size})."
                )

            entries.append(
                ArchiveEntry(
                    alias=alias,
                    method=method,
                    length=length,
                    compressed_length=compressed_length,
                    data_offset=data_offset,
                )
            )
            handle.seek(compressed_length, os.SEEK_CUR)

    return ArchiveInfo(
        path=archive_path,
        revision=revision,
        offset_padding=offset_padding,
        size_padding=size_padding,
        file_size=file_size,
        entries=entries,
    )


def read_entry_data_from_handle(handle: BinaryIO, entry: ArchiveEntry) -> bytes:
    handle.seek(entry.data_offset)
    payload = _read_exact(handle, entry.stored_length, entry.alias)
    if entry.method == METHOD_ZLIB:
        try:
            data = zlib.decompress(payload)
        except zlib.error as exc:
            raise ArchiveFormatError(f"Could not decompress {entry.alias!r}: {exc}") from exc
    else:
        data = payload

    if len(data) != entry.length:
        raise ArchiveFormatError(
            f"Entry {entry.alias!r} decoded to {len(data)} bytes, expected {entry.length}."
        )
    return data


def read_entry_data(path: os.PathLike[str] | str, entry: ArchiveEntry) -> bytes:
    with Path(path).open("rb") as handle:
        return read_entry_data_from_handle(handle, entry)


def safe_output_path(output_dir: Path, alias: str) -> Path:
    normalized = alias.replace("\\", "/")
    if PureWindowsPath(normalized).drive:
        raise ArchiveFormatError(f"Refusing to extract drive-qualified path: {alias!r}")

    posix_path = PurePosixPath(normalized)
    if posix_path.is_absolute():
        raise ArchiveFormatError(f"Refusing to extract absolute path: {alias!r}")
    if any(part in ("", ".", "..") for part in posix_path.parts):
        raise ArchiveFormatError(f"Refusing to extract unsafe path: {alias!r}")

    target = output_dir.joinpath(*posix_path.parts)
    root = output_dir.resolve()
    resolved_target = target.resolve(strict=False)
    try:
        resolved_target.relative_to(root)
    except ValueError as exc:
        raise ArchiveFormatError(f"Refusing to extract outside output directory: {alias!r}") from exc
    return target


def unpack_archive(
    path: os.PathLike[str] | str,
    output_dir: os.PathLike[str] | str,
    *,
    overwrite: bool = False,
    encoding: str = "utf-8",
    include: Optional[Sequence[str]] = None,
) -> UnpackResult:
    info = scan_archive(path, encoding=encoding)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    with info.path.open("rb") as handle:
        for entry in info.entries:
            if include and not any(fnmatch.fnmatch(entry.alias, pattern) for pattern in include):
                continue

            target = safe_output_path(out_root, entry.alias)
            if target.exists() and not overwrite:
                raise FileExistsError(f"Refusing to overwrite existing file: {target}")

            data = read_entry_data_from_handle(handle, entry)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append(target)

    return UnpackResult(archive=info.path, output_dir=out_root, entries=info.entries, written=written)


def _iter_input_files(
    input_dir: Path,
    archive_path: Path,
    excludes: Sequence[str],
) -> tuple[List[Path], List[Path], List[Path]]:
    files: List[Path] = []
    skipped_symlink: List[Path] = []
    skipped_excluded: List[Path] = []
    archive_resolved = archive_path.resolve(strict=False)

    for item in sorted(input_dir.rglob("*"), key=lambda p: p.relative_to(input_dir).as_posix().lower()):
        if item.is_symlink():
            skipped_symlink.append(item)
            continue
        if not item.is_file():
            continue
        if item.resolve(strict=False) == archive_resolved:
            skipped_excluded.append(item)
            continue

        alias = item.relative_to(input_dir).as_posix()
        if any(fnmatch.fnmatch(alias, pattern) for pattern in excludes):
            skipped_excluded.append(item)
            continue
        files.append(item)

    return files, skipped_symlink, skipped_excluded


def _write_entry(
    handle: BinaryIO,
    alias: str,
    data: bytes,
    *,
    compression_level: int,
    offset_padding: int,
    encoding: str,
) -> ArchiveEntry:
    alias_bytes = _encode_alias(alias, encoding)

    if compression_level >= 0:
        method = METHOD_ZLIB
        payload = zlib.compress(data, compression_level)
    else:
        method = METHOD_RAW
        payload = data

    _align_write(handle, offset_padding)
    _write_u32(handle, len(alias_bytes))

    _align_write(handle, offset_padding)
    handle.write(alias_bytes)

    _align_write(handle, offset_padding)
    handle.write(bytes([method]))

    _align_write(handle, offset_padding)
    _write_u32(handle, len(data))

    if method == METHOD_ZLIB:
        _align_write(handle, offset_padding)
        _write_u32(handle, len(payload))

    _align_write(handle, offset_padding)
    data_offset = handle.tell()
    handle.write(payload)

    return ArchiveEntry(
        alias=alias,
        method=method,
        length=len(data),
        compressed_length=len(payload),
        data_offset=data_offset,
    )


def pack_directory(
    input_dir: os.PathLike[str] | str,
    archive_path: os.PathLike[str] | str,
    *,
    compression_level: int = 6,
    offset_padding: int = 4,
    size_padding: int = 0,
    legacy: bool = False,
    overwrite: bool = False,
    encoding: str = "utf-8",
    excludes: Sequence[str] = (),
    raw_patterns: Sequence[str] = (),
    allow_empty: bool = False,
) -> PackResult:
    root = Path(input_dir)
    out_path = Path(archive_path)
    if not root.is_dir():
        raise NotADirectoryError(root)
    if not -1 <= compression_level <= 9:
        raise ValueError("compression_level must be -1 for raw, or 0..9 for zlib.")
    if offset_padding < 0 or size_padding < 0:
        raise ValueError("padding values must be >= 0.")
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing archive: {out_path}")

    files, skipped_symlink, skipped_excluded = _iter_input_files(root, out_path, excludes)
    skipped_empty: List[Path] = []
    entries: List[ArchiveEntry] = []

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as handle:
        if legacy:
            _write_u32(handle, MAGIC_LEGACY)
            effective_offset_padding = 0
        else:
            _write_u32(handle, MAGIC_ENHANCED)
            _write_u32(handle, offset_padding)
            _write_u32(handle, size_padding)
            effective_offset_padding = offset_padding

        for file_path in files:
            data = file_path.read_bytes()
            if not data and not allow_empty:
                skipped_empty.append(file_path)
                continue

            alias = file_path.relative_to(root).as_posix()
            entry_compression_level = (
                -1
                if any(fnmatch.fnmatch(alias, pattern) for pattern in raw_patterns)
                else compression_level
            )
            entries.append(
                _write_entry(
                    handle,
                    alias,
                    data,
                    compression_level=entry_compression_level,
                    offset_padding=effective_offset_padding,
                    encoding=encoding,
                )
            )

        # Mirrors nArchive::Close(): no offset alignment is applied before EOF.
        _write_u32(handle, 0xFFFFFFFF)

        if not legacy and size_padding:
            size = handle.tell()
            pad_count = size_padding - (size % size_padding)
            handle.write(b"\xff" * pad_count)

    return PackResult(
        archive=out_path,
        entries=entries,
        skipped_empty=skipped_empty,
        skipped_symlink=skipped_symlink,
        skipped_excluded=skipped_excluded,
    )


def compare_trees(left: os.PathLike[str] | str, right: os.PathLike[str] | str) -> List[str]:
    left_root = Path(left)
    right_root = Path(right)
    problems: List[str] = []

    left_files = {
        path.relative_to(left_root).as_posix(): path
        for path in left_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    right_files = {
        path.relative_to(right_root).as_posix(): path
        for path in right_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }

    for alias in sorted(set(left_files) | set(right_files)):
        if alias not in left_files:
            problems.append(f"Only in right: {alias}")
        elif alias not in right_files:
            problems.append(f"Only in left: {alias}")
        elif left_files[alias].read_bytes() != right_files[alias].read_bytes():
            problems.append(f"Content differs: {alias}")

    return problems


def filter_entries(entries: Iterable[ArchiveEntry], patterns: Sequence[str]) -> List[ArchiveEntry]:
    if not patterns:
        return list(entries)
    return [entry for entry in entries if any(fnmatch.fnmatch(entry.alias, pattern) for pattern in patterns)]
