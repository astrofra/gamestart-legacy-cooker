# GameStart Legacy Cooker

Command-line packers and unpackers for legacy GameStart `nArchive` packages
(`.nac` and `.gsa`). The repository contains both a Python implementation and
a standalone native C implementation.

This is focused on the archive container. In the old engine source,
`source/cooker` is an asset conversion layer used before packaging, while
`source/framework/archive` is the file package implementation consumed at
runtime.

## Install

From this project directory:

```powershell
python -m pip install -e .
```

You can also run the tool without installing:

```powershell
$env:PYTHONPATH = "src"
python -m gamestart_legacy_cooker --help
```

On Windows, the repository also includes a checkout-local wrapper:

```powershell
.\gamestart-cooker.cmd --help
```

## Native C Tool

The C implementation is in [c/gamestart_cooker.c](c/gamestart_cooker.c), with
vendored zlib sources under `third_party/zlib`.

Build it with CMake:

```powershell
cmake -S . -B build
cmake --build build --config Release
```

Then run:

```powershell
.\build\Release\gamestart-cooker-c.exe info "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac"
```

More details are in [docs/c-tool.md](docs/c-tool.md).

## Usage

Inspect an archive:

```powershell
python -m gamestart_legacy_cooker info "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac"
```

List files:

```powershell
python -m gamestart_legacy_cooker list "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac"
python -m gamestart_legacy_cooker list --include "data/sfx/*" --names-only "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac"
```

Unpack recursively:

```powershell
python -m gamestart_legacy_cooker unpack "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac" ".tmp\magnetis-unpacked" --overwrite
```

Pack a folder recursively:

```powershell
python -m gamestart_legacy_cooker pack ".tmp\magnetis-unpacked" ".tmp\magnetis-repacked.nac" --compression 6 --offset-padding 4 --overwrite
```

Compression uses zlib levels `0..9`. Use `--compression -1` for raw storage.
Use repeated `--raw` globs to keep only selected entries uncompressed:

```powershell
python -m gamestart_legacy_cooker pack ".tmp\magnetis-unpacked" ".tmp\magnetis-repacked.nac" --compression 6 --raw "data/sfx/*" --raw "data/music/*" --overwrite
```

The default enhanced archive layout uses 4-byte offset padding, matching the
Magnetis package tested during development.

## Format Logic

The package starts with a little-endian magic integer:

- `0x4E415244`, seen on disk as `DRAN`, for enhanced archives.
- `0x4E415243`, seen on disk as `CRAN`, for legacy archives.

Enhanced archives then store `offset_padding` and `size_padding`. Each file
entry stores an alias path, a method byte, original length, optional compressed
length, and then the raw or zlib-compressed payload. Paths inside the archive
use forward slashes.

More details are in [docs/format.md](docs/format.md).

## Source Context

The investigated engine code paths were:

- `source/cooker`: platform and texture asset conversion.
- `source/editor/publisher/editor_publisher.cpp`: recursive file collection,
  optional cooking, and archive writing.
- `source/framework/archive/archive.cpp`: `.nac`/`.gsa` package format.
- `source/framework/filesystem/io_archive.cpp`: runtime archive filesystem.

GameStart context from the public site is summarized in
[docs/context.md](docs/context.md).

The Magnetis validation run is summarized in [docs/testing.md](docs/testing.md).

## Development

Run tests:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
