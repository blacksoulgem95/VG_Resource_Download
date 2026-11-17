#!/usr/bin/env python3
"""
Versione dell'applicazione, in un posto solo.

La usano il launcher (`--version`), lo spec di PyInstaller (nome dei file e
metadati degli eseguibili) e gli script di packaging, che la leggono con

    python -c "import vg_version; print(vg_version.__version__)"

Version bump: cambia qui e tagga `vX.Y.Z` su git, così la release prende il
numero giusto.
"""

from __future__ import annotations

__version__ = "1.0.0"

APP_NAME = "VG Resource Download"
APP_ID = "vg-resource-download"
APP_DESCRIPTION = "Scarica tutti gli asset di un gioco da The Models Resource"
APP_PUBLISHER = "blacksoulgem95"
APP_HOMEPAGE = "https://github.com/blacksoulgem95/VG_Resource_Download"
