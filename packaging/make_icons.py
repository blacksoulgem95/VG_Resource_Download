#!/usr/bin/env python3
"""
Genera le icone native per il packaging a partire da `icons/web/icon-512.png`.

Produce in `packaging/icons/`:

    app.ico     Windows (16, 24, 32, 48, 64, 128, 256) — usato da NSIS e dall'exe
    app.icns    macOS: bundle di PNG nelle taglie che vuole il Finder
    app.png     512x512, per AppImage e per i file .desktop di Linux

Serve Pillow:

    pip install pillow
    python packaging/make_icons.py

L'ICNS viene scritto a mano: il formato è un'intestazione `icns` + lunghezza
seguita da blocchi (tipo a 4 byte, lunghezza, dati). Per le icone moderne i
dati sono PNG, quindi bastano Pillow e poche righe — niente `iconutil` (che
esiste solo su macOS).
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - dipende dall'ambiente
    sys.exit("Serve Pillow: pip install pillow")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / "icons" / "web" / "icon-512.png"
OUT_DIR = HERE / "icons"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

# Taglie ICNS in formato PNG: (tipo, lato in pixel).
# ic07..ic14 coprono 128 → 1024; icp4/icp5 sono le versioni piccole (16/32).
ICNS_ENTRIES = [
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
    ("ic11", 32),
    ("ic12", 64),
    ("ic13", 256),
    ("ic14", 512),
]


def load_source() -> "Image.Image":
    if not SOURCE.is_file():
        sys.exit(f"Icona sorgente non trovata: {SOURCE}")
    return Image.open(SOURCE).convert("RGBA")


def make_ico(image: "Image.Image", path: Path) -> None:
    biggest = max(ICO_SIZES)
    # Pillow vuole la tela più grande e ricava le altre taglie da sola.
    base = image.resize((biggest, biggest), Image.LANCZOS)
    base.save(path, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    print(f"  {path.relative_to(ROOT)}  ({len(ICO_SIZES)} taglie)")


def png_bytes(image: "Image.Image", size: int) -> bytes:
    import io

    buf = io.BytesIO()
    image.resize((size, size), Image.LANCZOS).save(buf, format="PNG")
    return buf.getvalue()


def make_icns(image: "Image.Image", path: Path) -> None:
    blocks = []
    for kind, size in ICNS_ENTRIES:
        data = png_bytes(image, size)
        # Lunghezza del blocco: 4 byte del tipo + 4 byte di lunghezza + dati.
        blocks.append(kind.encode("ascii") + struct.pack(">I", len(data) + 8) + data)

    body = b"".join(blocks)
    with path.open("wb") as handle:
        handle.write(b"icns")
        handle.write(struct.pack(">I", len(body) + 8))
        handle.write(body)
    print(f"  {path.relative_to(ROOT)}  ({len(ICNS_ENTRIES)} taglie)")


def make_png(image: "Image.Image", path: Path, size: int = 512) -> None:
    image.resize((size, size), Image.LANCZOS).save(path, format="PNG")
    print(f"  {path.relative_to(ROOT)}  ({size}x{size})")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Da {SOURCE.relative_to(ROOT)}:")
    image = load_source()
    make_ico(image, OUT_DIR / "app.ico")
    make_icns(image, OUT_DIR / "app.icns")
    make_png(image, OUT_DIR / "app.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
