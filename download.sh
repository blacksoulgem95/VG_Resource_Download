#!/usr/bin/env bash
#
# The Models Resource / VG Resource downloader (Linux e macOS) - launcher.
#
# Il sito è protetto da Cloudflare (challenge JavaScript "Just a moment..."):
# curl e requests ricevono sempre 403, quindi il lavoro viene delegato a un vero
# Chrome pilotato da Playwright (vg_download.py).
#
# Uso:
#   ./download.sh                 interfaccia grafica (tkinter)
#   ./download.sh --tui           interfaccia a terminale
#   ./download.sh --gui <url>     grafica con l'URL già compilato
#   ./download.sh <url> [...]     riga di comando (equivalente a vg_download.py)
#
# Nota su tkinter: non è un pacchetto pip, è un'estensione della standard
# library che deve fornire il Python di sistema. Il venv la vede da solo
# (condivide la stdlib), quindi non serve --system-site-packages. Se il modulo
# manca, questo script prova a prepararne una copia locale in .tk-bundle usando
# apt-get download + dpkg-deb -x, senza chiedere la password di root.

set -uo pipefail
cd "$(dirname "$0")" || exit 1

VENV=".venv"

if [ ! -x "$VENV/bin/python" ]; then
    echo "Preparo l'ambiente Python (solo la prima volta)..."
    if ! command -v python3 >/dev/null; then
        echo "ERRORE: python3 non trovato. Installalo (es. sudo apt install python3 python3-venv)."
        exit 1
    fi
    if ! python3 -m venv "$VENV"; then
        echo "ERRORE: impossibile creare il venv. Su Debian/Ubuntu serve: sudo apt install python3-venv"
        exit 1
    fi
fi

if ! "$VENV/bin/python" -c "import playwright" >/dev/null 2>&1; then
    echo "Installo playwright..."
    "$VENV/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
    if ! "$VENV/bin/pip" install --quiet playwright; then
        echo "ERRORE: installazione di playwright fallita."
        exit 1
    fi
fi

have_display() {
    [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]
}

have_tk() {
    "$VENV/bin/python" -c "import tkinter" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# tkinter locale senza root
#
# Il modulo fa parte della standard library ma è compilato: non si può fare
# `pip install tkinter`. Su Debian/Ubuntu arriva col pacchetto python3-tk.
# Qui lo estraiamo in .tk-bundle e puntiamo PYTHONPATH/LD_LIBRARY_PATH lì,
# così funziona anche senza sudo.
# ---------------------------------------------------------------------------
TK_BUNDLE=".tk-bundle"

bootstrap_tk() {
    if [ -n "$(find "$TK_BUNDLE" -name '_tkinter*.so' -print -quit 2>/dev/null)" ]; then
        return 0
    fi
    if ! command -v apt-get >/dev/null 2>&1 || ! command -v dpkg-deb >/dev/null 2>&1; then
        return 1
    fi

    local work
    work=$(mktemp -d) || return 1
    echo "tkinter non presente: ne preparo una copia locale in $TK_BUNDLE (senza sudo)..."

    if ! ( cd "$work" && apt-get download \
            python3-tk libtk8.6 libtcl8.6 tcl8.6 tk8.6 tk8.6-blt2.5 \
            >/dev/null 2>&1 ); then
        rm -rf "$work"
        return 1
    fi

    mkdir -p "$TK_BUNDLE"
    local deb
    for deb in "$work"/*.deb; do
        [ -e "$deb" ] || continue
        dpkg-deb -x "$deb" "$TK_BUNDLE" >/dev/null 2>&1
    done
    rm -rf "$work"

    [ -n "$(find "$TK_BUNDLE" -name '_tkinter*.so' -print -quit 2>/dev/null)" ]
}

tk_env_export() {
    local root="$TK_BUNDLE"
    local pyver pyroot extra libdirs tcl tk

    pyver=$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    pyroot="$root/usr/lib/python$pyver"

    extra=""
    [ -d "$pyroot/tkinter" ] && extra="$pyroot"
    [ -d "$pyroot/lib-dynload" ] && extra="${extra:+$extra:}$pyroot/lib-dynload"
    if [ -n "$extra" ]; then
        export PYTHONPATH="$extra${PYTHONPATH:+:$PYTHONPATH}"
    fi

    # GNU find: il bootstrap gira solo su sistemi con apt
    libdirs=$(find "$root" -name '*.so*' -printf '%h\n' 2>/dev/null | sort -u | tr '\n' ':')
    [ -n "$libdirs" ] && export LD_LIBRARY_PATH="$libdirs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    # Le librerie di script si trovano cercando i file che Tk/Tcl caricano
    # davvero. Il filtro *tcltk* esclude init.tcl estranei (es. quello di BLT)
    # e la dir in usr/lib/tcltk/*/tk8.6 che contiene solo pkgIndex.tcl.
    tcl=$(find "$root" -path '*tcltk*' -name 'init.tcl' -printf '%h\n' 2>/dev/null \
          | sort | head -n 1)
    tk=$(find "$root" -path '*tcltk*' -name 'tk.tcl' -printf '%h\n' 2>/dev/null \
         | sort | head -n 1)
    [ -n "$tcl" ] && export TCL_LIBRARY="$tcl"
    [ -n "$tk" ] && export TK_LIBRARY="$tk"
    return 0
}

# Rende tkinter utilizzabile: quella di sistema, oppure la copia locale.
ensure_tk() {
    have_tk && return 0
    bootstrap_tk || return 1
    tk_env_export
    have_tk
}

launch_gui() {
    exec "$VENV/bin/python" vg_gui.py "$@"
}

# --- modalità forzata a terminale
if [ "${1:-}" = "--tui" ]; then
    shift
    exec "$VENV/bin/python" vg_tui.py "$@"
fi

# --- grafica con URL precompilato
if [ "${1:-}" = "--gui" ]; then
    shift
    if have_display && ensure_tk; then
        launch_gui "$@"
    fi
    echo "Interfaccia grafica non disponibile: uso la modalità a terminale."
    exec "$VENV/bin/python" vg_tui.py "$@"
fi

# --- con argomenti: riga di comando classica
if [ $# -gt 0 ]; then
    exec "$VENV/bin/python" vg_download.py "$@"
fi

# --- nessun argomento: grafica se possibile, altrimenti terminale
if ! have_display; then
    echo "Nessun display grafico rilevato: uso la modalità a terminale."
else
    if ensure_tk; then
        launch_gui
    fi
    echo "tkinter non disponibile: uso la modalità a terminale."
    echo "Per la grafica: sudo apt install python3-tk"
fi
exec "$VENV/bin/python" vg_tui.py
