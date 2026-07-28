#!/usr/bin/env python3
"""Convert a Codex Pet spritesheet pack to py-shimeji's native PNG filenames."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from codex_pet import convert_codex_pet, is_codex_pack  # noqa: E402
from shimeji_pack import sprite_pack_kind  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a Codex Pet pack (pet.json + spritesheet) to py-shimeji PNG names."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Codex pet folder (pet.json and spritesheet.webp/png)",
    )
    parser.add_argument(
        "dest",
        type=Path,
        nargs="?",
        help="Output folder (default: assets/sprites/imported/<pack-name>)",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1

    kind = sprite_pack_kind(source)
    if kind == "none":
        print(
            "Source is not a Codex Pet pack (expected pet.json and spritesheet.webp/png).",
            file=sys.stderr,
        )
        return 1
    if kind == "native":
        print("Source already uses py-shimeji PNG names; nothing to convert.", file=sys.stderr)
        return 1
    if kind == "shimeji":
        print(
            "Source is a Shimeji pack — use scripts/convert_shimeji_pack.py instead.",
            file=sys.stderr,
        )
        return 1
    if not is_codex_pack(source):
        print("Source spritesheet could not be read.", file=sys.stderr)
        return 1

    dest = (
        args.dest.resolve()
        if args.dest
        else PROJECT_ROOT / "assets" / "sprites" / "imported" / source.name
    )
    if not convert_codex_pet(source, dest):
        print("Conversion failed — no frames could be mapped.", file=sys.stderr)
        return 1

    print(f"Converted Codex Pet pack to: {dest}")
    print("Select this folder in the tray menu (Change Pet N sprites...) or copy it elsewhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
