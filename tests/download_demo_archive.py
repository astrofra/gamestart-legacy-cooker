#!/usr/bin/env python3
"""
Download a public GameStart demo build, extract its native/000.gsa archive,
unpack it with the native cooker tool, and write the archive file list.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


DEMO_URL = (
    "https://github.com/astrofra/demo-within-the-mesh/releases/download/"
    "v1.1.0/mndrn-within-win32build.zip"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def log(message: str) -> None:
    print(message, flush=True)


def download(url: str, target: Path, force: bool) -> None:
    if target.exists() and not force:
        log(f"Using existing download: {target}")
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    if tmp.exists():
        tmp.unlink()

    log(f"Downloading {url}")
    with urllib.request.urlopen(url) as response, tmp.open("wb") as output:
        shutil.copyfileobj(response, output)
    tmp.replace(target)
    log(f"Saved {target}")


def safe_unzip(zip_path: Path, output_dir: Path, force: bool) -> None:
    if output_dir.exists() and force:
        shutil.rmtree(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        log(f"Using existing extraction: {output_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()

    log(f"Extracting {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (output_dir / member.filename).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(f"Refusing unsafe zip path: {member.filename}") from exc
        archive.extractall(output_dir)


def find_native_archive(extract_dir: Path) -> Path:
    matches = [
        path
        for path in extract_dir.rglob("000.gsa")
        if path.parent.name.lower() == "native" and path.is_file()
    ]
    if not matches:
        raise FileNotFoundError(f"Could not find native/000.gsa under {extract_dir}")
    if len(matches) > 1:
        log("Multiple native/000.gsa files found; using the first one:")
        for path in matches:
            log(f"  {path}")
    return matches[0]


def run_tool(tool: Path, *args: str, capture: bool = False) -> str:
    command = [str(tool), *args]
    result = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    return result.stdout if capture else ""


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    default_work = root / "tests" / "_work" / "within_the_mesh"

    parser = argparse.ArgumentParser(
        description="Download a demo build, unpack native/000.gsa, and write archive.txt."
    )
    parser.add_argument("--url", default=DEMO_URL, help="Demo zip URL.")
    parser.add_argument("--work-dir", type=Path, default=default_work, help="Working directory.")
    parser.add_argument(
        "--tool",
        type=Path,
        default=root / "bin" / "gamestart-cooker.exe",
        help="Path to gamestart-cooker executable.",
    )
    parser.add_argument("--force", action="store_true", help="Re-download and re-extract.")
    args = parser.parse_args(argv)

    tool = args.tool.resolve()
    if not tool.is_file():
        raise FileNotFoundError(f"Native cooker tool not found: {tool}")

    work_dir = args.work_dir.resolve()
    zip_path = work_dir / "download" / "demo.zip"
    extract_dir = work_dir / "extracted"
    unpack_dir = work_dir / "unpacked"
    archive_txt = work_dir / "archive.txt"

    download(args.url, zip_path, args.force)
    safe_unzip(zip_path, extract_dir, args.force)

    archive_path = find_native_archive(extract_dir)
    log(f"Found archive: {archive_path}")

    if unpack_dir.exists():
        shutil.rmtree(unpack_dir)
    unpack_dir.mkdir(parents=True, exist_ok=True)

    listing = run_tool(tool, "list", "--names-only", str(archive_path), capture=True)
    archive_txt.write_text(listing, encoding="utf-8", newline="\n")
    log(f"Wrote archive file list: {archive_txt}")

    run_tool(tool, "unpack", str(archive_path), str(unpack_dir), "--overwrite")
    log(f"Unpacked archive to: {unpack_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
