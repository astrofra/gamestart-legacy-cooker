# GameStart3D Legacy Cooker

Standalone command-line tool for legacy GameStart `nArchive` packages
(`.nac` and `.gsa`).

This project is focused on the archive container. In the old GameStart source,
`source/cooker` converts individual assets before packaging, while
`source/framework/archive` implements the package format read by the runtime.

The original GameStart cooker/archive code was authored by Emmanuel Julien:
https://github.com/ejulien/

## Layout

- `src/gamestart_cooker.c`: native command-line implementation.
- `third_party/zlib`: vendored zlib sources used for compressed entries.
- `docs/format.md`: archive format notes.
- `docs/context.md`: source and project context.
- `bin/`: built Windows executable and runtime readme.

## Build

With CMake:

```powershell
cmake -S . -B build
cmake --build build --config Release
```

The build writes `gamestart-cooker.exe` to `bin\`.

Direct MSVC build from a developer shell:

```powershell
cl /O2 /MT /I third_party\zlib src\gamestart_cooker.c third_party\zlib\adler32.c third_party\zlib\compress.c third_party\zlib\crc32.c third_party\zlib\deflate.c third_party\zlib\inffast.c third_party\zlib\inflate.c third_party\zlib\inftrees.c third_party\zlib\trees.c third_party\zlib\uncompr.c third_party\zlib\zutil.c /Fe:bin\gamestart-cooker.exe
```

## Usage

Inspect an archive:

```powershell
bin\gamestart-cooker.exe info game.nac
```

List files:

```powershell
bin\gamestart-cooker.exe list game.nac
bin\gamestart-cooker.exe list --include "data/music/*" --names-only game.nac
```

Unpack recursively:

```powershell
bin\gamestart-cooker.exe unpack game.nac unpacked --overwrite
```

Pack a folder recursively:

```powershell
bin\gamestart-cooker.exe pack unpacked repacked.nac --compression 6 --offset-padding 4 --overwrite
```

Compression uses zlib levels `0..9`. Use `--compression -1` for raw storage.
Use repeated `--raw` globs when selected entries should remain uncompressed:

```powershell
bin\gamestart-cooker.exe pack unpacked repacked.nac --compression 6 --raw "data/sfx/*" --raw "data/music/*" --overwrite
```

More details are in `docs\format.md`.
