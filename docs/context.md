# Context

GameStart was a 2D and 3D game engine/editor with runtime resource packaging.
The public website is available at https://coaching-games.net/.

The old source tree separates the workflow into two parts:

- `source/cooker`: platform-specific resource conversion before packaging.
- `source/framework/archive`: the `nArchive` package container consumed by the runtime.

The tool in this repository implements the package container as a standalone
command-line program. It does not attempt to reproduce texture conversion or
platform publishing steps.

The original GameStart cooker/archive code was authored by Emmanuel Julien:
https://github.com/ejulien/
