#!/usr/bin/env python3
"""
Dove l'app tiene i suoi file, quando è installata.

Eseguita dal sorgente, l'app scrive tutto accanto a sé (`.chrome-profile/`,
`download/`), comodo per chi sviluppa. Installata in `C:\\Program Files`,
in `/opt` o in un `.app`, la cartella dell'eseguibile è **di sola lettura**:
lì il profilo Chrome non potrebbe essere creato e il download fallirebbe
subito.

Quando gira impacchettata (`sys.frozen`) si usano quindi le cartelle utente:

    Windows   %LOCALAPPDATA%\\vg-resource-download\\chrome-profile
              %USERPROFILE%\\Downloads\\VG Resource Download
    macOS     ~/Library/Application Support/vg-resource-download/chrome-profile
              ~/Downloads/VG Resource Download
    Linux     ~/.local/share/vg-resource-download/chrome-profile
              ~/Downloads/VG Resource Download

Si può sempre forzare tutto con `VG_PROFILE` e con `-o/--out`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "vg-resource-download"

# Nome della cartella dei download creata accanto a "Scaricati".
DOWNLOADS_SUBDIR = "VG Resource Download"

# Quando non è impacchettata, l'app resta "portatile" nella sua cartella.
SOURCE_PROFILE = ".chrome-profile"
SOURCE_DOWNLOAD_DIR = "download"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """Cartella di configurazione/dati dell'utente (creata se serve)."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME


def user_downloads_dir() -> Path:
    """La cartella "Scaricati" dell'utente, meglio che si riesca a indovinare."""
    try:
        import subprocess

        if sys.platform == "darwin":
            # Su macOS la cartella si può essere spostata: lo dice il sistema.
            out = subprocess.run(
                ["defaults", "read", "com.apple.macl", "NSDownloadsFolderPath"],
                capture_output=True, text=True, timeout=2,
            )
            if out.returncode == 0 and out.stdout.strip():
                candidate = Path(os.path.expanduser(out.stdout.strip()))
                if candidate.is_dir():
                    return candidate
        elif os.name != "nt":
            # XDG: `xdg-user-dir DOWNLOAD` rispetta la lingua dell'utente.
            out = subprocess.run(
                ["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=2,
            )
            candidate = Path(out.stdout.strip()) if out.returncode == 0 else None
            if candidate and str(candidate) != str(Path.home()) and candidate.is_dir():
                return candidate
    except Exception:
        pass
    return Path.home() / "Downloads"


def default_download_dir() -> Path:
    """Cartella base dei download quando non se ne indica una."""
    env = os.environ.get("VG_DOWNLOAD_DIR")
    if env:
        return Path(os.path.expanduser(env))
    if is_frozen():
        return user_downloads_dir() / DOWNLOADS_SUBDIR
    return Path(SOURCE_DOWNLOAD_DIR)


def default_profile_dir() -> str:
    """Profilo Chrome persistente: contiene il cookie `cf_clearance`."""
    env = os.environ.get("VG_PROFILE")
    if env:
        return os.path.expanduser(env)
    if is_frozen():
        return str(user_data_dir() / "chrome-profile")
    return SOURCE_PROFILE


def ensure_dir(path: Path) -> Path:
    """mkdir -p tollerante: se non si può creare, si proverà comunque a usarla."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path
