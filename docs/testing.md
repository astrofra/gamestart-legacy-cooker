# Testing Notes

Validated against:

```text
E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac
```

Observed archive metadata:

- revision: `EnhancedLegacy`
- offset padding: `4`
- size padding: `0`
- entries: `504`
- original payload size: `21.73 MB`
- stored payload size: `13.95 MB`
- archive file size: `13.98 MB`
- raw entries: `42`

The raw entries in Magnetis are audio files under:

- `data/sfx/*`
- `data/music/*`

Validation steps run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
python -m gamestart_legacy_cooker info "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac"
python -m gamestart_legacy_cooker unpack "E:\_games_by_others_\yullaby\magnetis\game\bin\data\magnetis.nac" ".tmp\magnetis-unpacked" --overwrite
python -m gamestart_legacy_cooker pack ".tmp\magnetis-unpacked" ".tmp\magnetis-repacked-raw-audio.nac" --compression 6 --offset-padding 4 --raw "data/sfx/*" --raw "data/music/*" --overwrite
python -m gamestart_legacy_cooker unpack ".tmp\magnetis-repacked-raw-audio.nac" ".tmp\magnetis-repacked-raw-audio-unpacked" --overwrite
```

The unpacked original tree matched the unpacked repack byte-for-byte.

## Native C Tool Status

The C source, CMake project, and vendored zlib source are included. This
machine did not have `cmake`, MSVC `cl`, or `gcc` on `PATH` during the native
tool implementation, so a full native executable build should be run in a
developer shell with one of those toolchains installed.

The legacy tree's bundled TCC was able to compile `c/gamestart_cooker.c` and
the vendored zlib sources to object files, which validates syntax and include
coverage. It could not link an executable in this environment because its
startup/runtime objects were not configured on `PATH`.
