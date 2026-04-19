# Context

GameStart was a 2D and 3D game engine/editor. The public website is still
available at https://coaching-games.net/.

Useful public context from that site:

- The documentation page describes GameStart documentation as split between
  the editor, the framework, and application scripting:
  https://coaching-games.net/content/documentation.html
- The download page describes the old Windows editor beta and sample package:
  https://coaching-games.net/content/download.html
- The FAQ describes GameStart as covering 3D, 2D, audio, physics, resource
  management, and scripting, and lists Magnetis among shipped projects:
  https://coaching-games.net/content/faq.html

The local source tree matches that split. The publisher gathers runtime and
project files, optionally runs a platform cooker on each resource, then writes
the final package with `nArchive`. Magnetis ships a `magnetis.nac` package
using this archive format.

