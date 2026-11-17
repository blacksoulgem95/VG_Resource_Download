# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller — un solo file, tre sistemi.

Costruisce un bundle *onedir* con dentro:

    vgdl                 launcher completo (CLI + TUI + GUI)
    _internal/           Python, Playwright e le icone

Su Windows aggiunge un secondo eseguibile, `VG Resource Download.exe`, senza
console: è quello che apre il menu Start (avviare quello a console da doppio
clic mostrerebbe una finestra nera dietro la GUI).

Su macOS il bundle viene avvolto in un `.app` (BUNDLE) con Info.plist e .icns.

Uso:
    pyinstaller --noconfirm --clean packaging/vgdl.spec

L'uscita è in dist/VGResourceDownload/ (+ dist/VG Resource Download.app su macOS).
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH lo mette PyInstaller
ICONS = ROOT / "packaging" / "icons"
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
COLLECT_NAME = "VGResourceDownload"


# --------------------------------------------------------------------------
# Versione (letta dal sorgente, così c'è un solo posto da aggiornare)
# --------------------------------------------------------------------------
def read_version() -> str:
    namespace: dict = {}
    source = (ROOT / "vg_version.py").read_text(encoding="utf-8")
    exec(compile(source, "vg_version.py", "exec"), namespace)  # noqa: S102
    return str(namespace["__version__"])


VERSION = read_version()
VERSION_TUPLE = tuple(int(part) for part in VERSION.split(".")) + (0,) * (4 - VERSION.count(".") - 1)
VERSION_TUPLE = VERSION_TUPLE[:4]


# --------------------------------------------------------------------------
# Playwright: porta con sé il driver Node. I browser NON servono, l'app usa il
# Chrome installato dall'utente (`find_chrome()` in vg_download.py).
# --------------------------------------------------------------------------
pw_datas, pw_binaries, pw_hidden = collect_all("playwright")


# --------------------------------------------------------------------------
# Metadati dell'eseguibile Windows (Proprietà → Dettagli del file .exe)
# --------------------------------------------------------------------------
def windows_version_file() -> str | None:
    if not IS_WIN:
        return None
    path = ROOT / "packaging" / "build" / "windows_version_info.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    numbers = ", ".join(str(part) for part in VERSION_TUPLE)
    path.write_text(
        f"""# Generato da packaging/vgdl.spec
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numbers}),
    prodvers=({numbers}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'blacksoulgem95'),
          StringStruct('FileDescription', 'VG Resource Download'),
          StringStruct('FileVersion', '{VERSION}'),
          StringStruct('InternalName', 'vg-resource-download'),
          StringStruct('LegalCopyright', 'MIT License'),
          StringStruct('OriginalFilename', 'VG Resource Download.exe'),
          StringStruct('ProductName', 'VG Resource Download'),
          StringStruct('ProductVersion', '{VERSION}'),
        ],
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
""",
        encoding="utf-8",
    )
    return str(path)


EXCLUDES = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "IPython",
    "PIL",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "pytest",
    "setuptools",
    "pip",
    "wheel",
]

analysis = Analysis(  # noqa: F821
    [str(ROOT / "vg_launcher.py")],
    pathex=[str(ROOT)],
    binaries=pw_binaries,
    datas=pw_datas + [(str(ROOT / "icons"), "icons")],
    hiddenimports=pw_hidden
    + [
        "vg_download",
        "vg_gui",
        "vg_tui",
        "vg_i18n",
        "vg_icons",
        "vg_paths",
        "vg_version",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
    ],
    hookspath=[str(ROOT / "packaging" / "hooks")],
    runtime_hooks=[str(ROOT / "packaging" / "hooks" / "rth_playwright.py")],
    excludes=EXCLUDES,
    noarchive=False,
)

pyz = PYZ(analysis.pure)  # noqa: F821

common = dict(
    upx=False,
    strip=False,
    debug=False,
    bootloader_ignore_signals=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --- eseguibile principale: console, così CLI e TUI funzionano ovunque -------
main_exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="vgdl",
    console=True,
    icon=str(ICONS / ("app.ico" if IS_WIN else "app.png")) if not IS_MAC else None,
    **common,
)

targets = [main_exe]

# --- Windows: secondo exe senza console, per il doppio clic ------------------
if IS_WIN:
    gui_exe = EXE(
        pyz,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="VG Resource Download",
        console=False,
        icon=str(ICONS / "app.ico"),
        version=windows_version_file(),
        **common,
    )
    targets.append(gui_exe)

collect = COLLECT(  # noqa: F821
    *targets,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name=COLLECT_NAME,
)

# --- macOS: avvolge il tutto in un .app con Info.plist e icona --------------
if IS_MAC:
    app = BUNDLE(  # noqa: F821
        collect,
        # Il nome viene usato alla lettera: BUNDLE fa
        # os.path.join(distpath, basename(name)) e *non* aggiunge ".app".
        # Con "VG Resource Download" uscirebbe una cartella senza estensione,
        # che il Finder non tratta come applicazione.
        name="VG Resource Download.app",
        icon=str(ICONS / "app.icns"),
        bundle_identifier="com.blacksoulgem95.vg-resource-download",
        version=VERSION,
        info_plist={
            "CFBundleName": "VG Resource Download",
            "CFBundleDisplayName": "VG Resource Download",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "CFBundleGetInfoString": f"VG Resource Download {VERSION}",
            "NSHumanReadableCopyright": "MIT License",
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSApplicationCategoryType": "public.app-category.utilities",
        },
    )
