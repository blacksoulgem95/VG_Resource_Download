#!/usr/bin/env python3
"""
Icona dell'applicazione.

I file stanno in `icons/` (il pacchetto generato per web, Android e iOS):

    icons/web/icon-512.png     icona grande
    icons/web/icon-192.png     icona media
    icons/web/favicon.ico      16x16 + 32x32 per Windows

`apply_window_icon(finestra)` imposta l'icona della finestra tkinter usando il
formato migliore disponibile: .ico su Windows, PNG altrove. Si può forzare un
file con la variabile d'ambiente `VG_ICON=/percorso/icona`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent / "icons"

# Ordine di preferenza: prima i PNG (netti anche in alto), poi l'ico.
PNG_ORDER = ("icon-192.png", "icon-512.png")
ICO_ORDER = ("favicon.ico",)

# Sottocartelle note, oltre a icons/ stesso, dove cercare i file.
SEARCH_DIRS = (
    ICONS_DIR / "web",
    ICONS_DIR,
)


def _env_icon() -> Path | None:
    raw = os.environ.get("VG_ICON")
    if not raw:
        return None
    path = Path(os.path.expanduser(raw))
    return path if path.is_file() else None


def find_icon(extensions: tuple[str, ...] = ("png", "ico")) -> Path | None:
    """Restituisce il primo file icona trovato con una delle estensioni date."""
    forced = _env_icon()
    if forced is not None:
        return forced

    for directory in SEARCH_DIRS:
        for name in (*PNG_ORDER, *ICO_ORDER):
            if Path(name).suffix.lstrip(".").lower() not in extensions:
                continue
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def icon_files() -> list[Path]:
    """Tutti i file icona disponibili, dal più piccolo al più grande."""
    found: list[Path] = []
    for directory in SEARCH_DIRS:
        for name in (*PNG_ORDER, *ICO_ORDER):
            candidate = directory / name
            if candidate.is_file() and candidate not in found:
                found.append(candidate)
    return found


def apply_window_icon(window) -> bool:
    """Imposta l'icona di una finestra tkinter. True se ci è riuscito."""
    forced = _env_icon()
    if forced is not None:
        return _apply_path(window, forced)

    # Su Windows l'iconbitmap(.ico) dà anche l'icona nella barra delle applicazioni.
    if os.name == "nt":
        for name in ICO_ORDER:
            for directory in SEARCH_DIRS:
                candidate = directory / name
                if candidate.is_file() and _apply_path(window, candidate):
                    return True

    pngs = [p for p in icon_files() if p.suffix.lower() == ".png"]
    if pngs and _apply_pngs(window, pngs):
        return True

    for path in icon_files():
        if _apply_path(window, path):
            return True
    return False


def _apply_pngs(window, paths: list[Path]) -> bool:
    """Dà a Tk più dimensioni: il window manager sceglie quella giusta."""
    try:
        import tkinter as tk
    except Exception:
        return False

    images = []
    for path in paths:
        try:
            images.append(tk.PhotoImage(file=str(path)))
        except Exception:
            continue
    if not images:
        return False

    try:
        window.iconphoto(True, *images)
    except Exception:
        return False

    # I PhotoImage vanno tenuti vivi finché la finestra esiste.
    window._vg_icon_image = images  # type: ignore[attr-defined]
    return True


def _apply_path(window, path: Path) -> bool:
    try:
        import tkinter as tk
    except Exception:
        return False

    suffix = path.suffix.lower()
    try:
        if suffix == ".ico":
            # iconbitmap vuole un percorso; su X11 può non essere supportato.
            window.iconbitmap(default=str(path))
            return True
        image = tk.PhotoImage(file=str(path))
    except Exception:
        return False

    try:
        # iconphoto(default=True, ...) vale per tutte le finestre dell'app.
        window.iconphoto(True, image)
    except Exception:
        return False

    # Il PhotoImage va tenuto vivo finché la finestra esiste.
    window._vg_icon_image = image  # type: ignore[attr-defined]
    return True


if __name__ == "__main__":
    for item in icon_files():
        print(f"{item.relative_to(Path.cwd()) if item.is_relative_to(Path.cwd()) else item}"
              f"  ({item.stat().st_size / 1024:.0f} KB)")
    if not icon_files():
        print("nessuna icona trovata in", ICONS_DIR, file=sys.stderr)
