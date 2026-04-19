GameStart Legacy Cooker
=======================

gamestart-cooker.exe is a standalone command-line tool for legacy GameStart
nArchive packages (.nac and .gsa).

Original GameStart cooker/archive author:
Emmanuel Julien
https://github.com/ejulien/

Basic commands:

  gamestart-cooker.exe info game.nac
  gamestart-cooker.exe list game.nac
  gamestart-cooker.exe unpack game.nac unpacked --overwrite
  gamestart-cooker.exe pack unpacked repacked.nac --compression 6 --overwrite

Useful pack options:

  --compression N       zlib level 0..9, or -1 for raw storage
  --raw PATTERN         keep matching archive paths uncompressed
  --exclude PATTERN     skip matching input paths
  --offset-padding N    enhanced archive alignment, default 4
  --legacy              write the older legacy header

Archive paths use forward slashes. Extraction rejects absolute paths and
directory traversal entries.
