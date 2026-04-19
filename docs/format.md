# GameStart nArchive Format

This project targets the archive container used by the legacy GameStart engine.
The relevant source files in the old tree are:

- `source/framework/archive/archive.cpp` and `archive.h`: container read/write logic.
- `source/framework/filesystem/io_archive.cpp`: runtime filesystem adapter.
- `source/editor/publisher/editor_publisher.cpp`: editor publishing flow.
- `source/cooker/*.cpp`: optional asset conversion before packaging.

The important split is that `source/cooker` does not define the package file
format. It converts individual resources, mostly textures, then the editor
publisher stores the resulting files in an `nArchive`.

The original GameStart cooker/archive code was authored by Emmanuel Julien:
https://github.com/ejulien/

## Header

All integer fields observed in Windows-built archives are little-endian 32-bit
values.

- Enhanced archives write the integer `0x4E415244`. On disk this appears as
  bytes `44 52 41 4E`, or ASCII `DRAN`, because the engine writes the integer
  on a little-endian machine. The source comment names it `NARD`.
- Legacy archives write `0x4E415243`, appearing as `CRAN`. The source comment
  names it `NARC`.
- Enhanced archives then store `offset_padding` and `size_padding` as 32-bit
  unsigned integers.

## Entries

Each entry is stored as:

1. Align the cursor to `offset_padding`.
2. `uint32`: alias byte length. Values greater than 511 stop the scanner.
3. Align, then alias bytes. Paths use forward slashes.
4. Align, then `uint8`: method. Bit 0 is used by the original reader.
5. Align, then `uint32`: original length.
6. If method is zlib, align, then `uint32`: compressed length.
7. Align, then payload bytes.

Methods:

- `0`: raw payload.
- `1`: zlib payload created with `compress2`.

The writer appends `0xffffffff` as an end marker, but the old `Close()` code
does not align before writing it. The parser checks for that unaligned marker
before applying normal entry alignment.

## Packing Policy

The original editor used zlib levels selected by the publishing profile:

- low: `1`
- average: `6`
- high: `9`

This CLI defaults to `6`. Use `--compression -1` to write raw entries. Empty
files are skipped by default because the original `MemoryBlockWrite` rejected
zero-length inputs; `--allow-empty` can force them into a new archive.

The archive supports per-entry methods. Use repeated `--raw` globs when only
some files should stay uncompressed, for example audio streams:

```powershell
bin\gamestart-cooker.exe pack unpacked game.nac --raw "data/sfx/*" --raw "data/music/*"
```

## Format Limits

- Alias length is limited to 511 bytes by the original reader.
- No timestamps, file permissions, or directory entries are stored.
- Path aliases are stored as archive-local forward-slash paths.
