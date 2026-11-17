# -*- coding: utf-8 -*-
"""Runtime hook: rende eseguibile il driver Node di Playwright.

PyInstaller copia i file di dati senza i permessi originali, quindi dentro il
bundle `playwright/driver/node` può finire senza bit di esecuzione e Playwright
fallisce con "Permission denied" all'avvio.

Questo hook gira prima del codice dell'app e sistema i permessi.
"""

import os
import stat
import sys

_DRIVER_NAMES = ("node", "node.exe")


def _candidate_dirs() -> list[str]:
    dirs: list[str] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(meipass)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if exe_dir:
        dirs.append(exe_dir)
    return dirs


def _fix_permissions() -> None:
    if os.name == "nt":
        # Su Windows l'eseguibilità non dipende dai permessi del file.
        return

    for base in _candidate_dirs():
        driver = os.path.join(base, "playwright", "driver")
        if not os.path.isdir(driver):
            continue
        for name in _DRIVER_NAMES:
            target = os.path.join(driver, name)
            if not os.path.isfile(target):
                continue
            try:
                mode = os.stat(target).st_mode
                # +x per utente, gruppo e altri (come farebbe `chmod +x`).
                os.chmod(target, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                pass


_fix_permissions()
