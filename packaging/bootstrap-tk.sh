#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Prepara tkinter per la build, senza sudo.
#
# PyInstaller può includere tkinter solo se il Python che esegue la build lo
# vede. Su Debian/Ubuntu il pacchetto `python3-tk` a volte manca (soprattutto
# se il Python viene da actions/setup-python): qui lo scarichiamo con
# `apt-get download` e lo estraiamo in `.tk-bundle/`, come fa `download.sh`.
#
# Uso:
#   packaging/bootstrap-tk.sh              # stampa KEY=VALUE per $GITHUB_ENV
#   packaging/bootstrap-tk.sh --export     # stampa righe "export ..." per eval
#   eval "$(packaging/bootstrap-tk.sh --export)"
#
# Se tkinter è già disponibile non stampa nulla ed esce con 0.
# Esce con 1 se non riesce a procurarlo (la build può proseguire senza GUI).
# ---------------------------------------------------------------------------

set -uo pipefail

TK_BUNDLE="${TK_BUNDLE:-.tk-bundle}"
PYTHON="${PYTHON:-python3}"
FORMAT="plain"
[ "${1:-}" = "--export" ] && FORMAT="export"

# Percorso assoluto: la variabile finisce nei file di ambiente della CI.
TK_BUNDLE="$(pwd)/$TK_BUNDLE"

_tk_ok() {
    "$PYTHON" -c 'import tkinter' >/dev/null 2>&1
}

# GNU find: il bootstrap gira solo su sistemi con apt.
_bootstrap() {
    if [ -n "$(find "$TK_BUNDLE" -name '_tkinter*.so' -print -quit 2>/dev/null)" ]; then
        return 0
    fi
    command -v apt-get >/dev/null 2>&1 || return 1
    command -v dpkg-deb >/dev/null 2>&1 || return 1

    local work
    work=$(mktemp -d) || return 1
    echo "tkinter assente: lo estraggo in $TK_BUNDLE" >&2

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

_emit() {
    local format="$1" name="$2" value="$3"
    [ -n "$value" ] || return 0
    if [ "$format" = "export" ]; then
        printf 'export %s="%s"\n' "$name" "$value"
    else
        printf '%s=%s\n' "$name" "$value"
    fi
}

# Calcola e stampa le variabili d'ambiente necessarie a vedere tkinter.
# $1: "plain" (KEY=VALUE, per $GITHUB_ENV) oppure "export" (per eval).
_env_exports() {
    local format="${1:-$FORMAT}" pyver pyroot extra libdirs tcl tk
    pyver=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])') || return 1
    pyroot="$TK_BUNDLE/usr/lib/python$pyver"

    extra=""
    [ -d "$pyroot/tkinter" ] && extra="$pyroot"
    [ -d "$pyroot/lib-dynload" ] && extra="${extra:+$extra:}$pyroot/lib-dynload"

    libdirs=$(find "$TK_BUNDLE" -name '*.so*' -printf '%h\n' 2>/dev/null \
              | sort -u | tr '\n' ':')
    tcl=$(find "$TK_BUNDLE" -path '*tcltk*' -name 'init.tcl' -printf '%h\n' 2>/dev/null \
          | sort | head -n 1)
    tk=$(find "$TK_BUNDLE" -path '*tcltk*' -name 'tk.tcl' -printf '%h\n' 2>/dev/null \
         | sort | head -n 1)

    [ -n "$extra" ] && _emit "$format" PYTHONPATH "${extra}${PYTHONPATH:+:$PYTHONPATH}"
    [ -n "$libdirs" ] && _emit "$format" LD_LIBRARY_PATH "${libdirs}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    [ -n "$tcl" ] && _emit "$format" TCL_LIBRARY "$tcl"
    [ -n "$tk" ] && _emit "$format" TK_LIBRARY "$tk"
    return 0
}

main() {
    if _tk_ok; then
        echo "tkinter già disponibile in $PYTHON" >&2
        return 0
    fi
    if ! _bootstrap; then
        echo "ERRORE: tkinter non disponibile e non scaricabile (serve apt-get)." >&2
        echo "La build proseguirà senza GUI (solo CLI e TUI)." >&2
        return 1
    fi

    local assignments
    assignments="$(_env_exports "$FORMAT")" || return 1
    printf '%s\n' "$assignments"

    # Verifica vera: le variabili vanno *esportate* (un semplice
    # `VAR=...` resta una variabile di shell e il figlio Python non la vede).
    eval "$(_env_exports export)" || return 1
    if ! _tk_ok; then
        echo "ERRORE: tkinter estratto ma non importabile." >&2
        return 1
    fi

    echo "tkinter preparato da $TK_BUNDLE" >&2
    return 0
}

main
