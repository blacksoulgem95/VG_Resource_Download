#!/usr/bin/env python3
"""
Punto d'ingresso unico della versione impacchettata (PyInstaller).

Fa lo stesso lavoro di `download.sh`, ma senza shell e senza venv:

    VG Resource Download        → interfaccia grafica (se c'è un display)
    VG Resource Download --tui  → interfaccia a terminale
    VG Resource Download URL    → riga di comando (qualsiasi altra opzione)

Senza display (o senza tkinter) si passa da soli alla versione a terminale,
come fanno i launcher.

Nota: gli import sono volutamente dentro le funzioni. tkinter può mancare
(es. Linux senza python3-tk) e non deve far fallire la modalità a terminale.
"""

from __future__ import annotations

import os
import sys

GUI_FLAGS = ("--gui", "-g")
TUI_FLAGS = ("--tui", "-t")


def has_display() -> bool:
    """C'è un server grafico su cui aprire la finestra?"""
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def tk_available() -> bool:
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def run_gui(argv: list[str]) -> int:
    import vg_gui

    return vg_gui.main(argv)


def run_tui(argv: list[str]) -> int:
    import vg_tui

    return vg_tui.main(argv)


def run_cli(argv: list[str]) -> int:
    import vg_download

    return vg_download.main(argv)


def gui_or_tui(argv: list[str], announce: bool = False) -> int:
    """GUI se possibile, altrimenti TUI (con un messaggio se richiesto)."""
    if has_display() and tk_available():
        return run_gui(argv)
    if announce and not tk_available():
        print("tkinter non disponibile: uso la modalità a terminale.")
    elif announce:
        print("Nessun display grafico rilevato: uso la modalità a terminale.")
    return run_tui(argv)


def main(argv: list[str]) -> int:
    args = list(argv)

    if "--version" in args or "-V" in args:
        from vg_version import __version__

        print(f"VG Resource Download {__version__}")
        return 0

    if args and args[0] in GUI_FLAGS:
        return gui_or_tui(args[1:], announce=True)

    if args and args[0] in TUI_FLAGS:
        return run_tui(args[1:])

    if args:
        return run_cli(args)

    return gui_or_tui([], announce=True)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
