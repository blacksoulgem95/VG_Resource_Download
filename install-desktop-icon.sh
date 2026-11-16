#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Mette l'icona e le voci di menu su Linux, senza sudo.
#
# Copia le icone da icons/web/ nella cartella delle icone dell'utente e crea
# due voci nel menu delle applicazioni:
#
#   VG Resource Download          apre la GUI
#   VG Resource Download (TUI)    apre la versione a terminale
#
# Uso:
#   ./install-desktop-icon.sh            installa (o aggiorna)
#   ./install-desktop-icon.sh --uninstall  rimuove tutto
#   ./install-desktop-icon.sh --help
#
# Su macOS e Windows non serve: lì l'icona è nella finestra della GUI.
# ---------------------------------------------------------------------------
set -euo pipefail

APP_ID="vg-resource-download"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_ROOT="$DATA_HOME/icons/hicolor"
APPS_DIR="$DATA_HOME/applications"

GUI_ENTRY="$APPS_DIR/$APP_ID.desktop"
TUI_ENTRY="$APPS_DIR/$APP_ID-tui.desktop"

say() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

usage() {
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# --------------------------------------------------------------------- icone
install_icons() {
    if [ ! -f "$HERE/icons/web/icon-512.png" ]; then
        err "Icone non trovate in $HERE/icons/web/"
        return 1
    fi
    if [ -f "$HERE/icons/web/icon-192.png" ]; then
        install -Dm644 "$HERE/icons/web/icon-192.png" \
            "$ICON_ROOT/192x192/apps/$APP_ID.png"
    fi
    install -Dm644 "$HERE/icons/web/icon-512.png" \
        "$ICON_ROOT/512x512/apps/$APP_ID.png"
    say "Icone installate in $ICON_ROOT"
}

remove_icons() {
    rm -f "$ICON_ROOT/192x192/apps/$APP_ID.png" \
          "$ICON_ROOT/512x512/apps/$APP_ID.png"
    rmdir "$ICON_ROOT/192x192/apps" "$ICON_ROOT/192x192" 2>/dev/null || true
    rmdir "$ICON_ROOT/512x512/apps" "$ICON_ROOT/512x512" 2>/dev/null || true
}

# --------------------------------------------------------------------- voci
# In un file .desktop le virgolette singole non si possono usare nell'Exec,
# quindi il percorso va protetto a mano.
escaped_dir() {
    printf '%s' "$HERE" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/%/%%/g'
}

write_entry() {
    local path="$1" name="$2" comment="$3" exec="$4" terminal="$5"
    local dir
    dir="$(escaped_dir)"

    mkdir -p "$APPS_DIR"
    cat > "$path" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$name
Comment=$comment
Comment[it]=Scarica tutti gli asset di un gioco da The Models Resource
Comment[fr]=Télécharge toutes les ressources d'un jeu depuis The Models Resource
Exec=bash -c "cd \\"$dir\\" && $exec"
Path=$dir
Icon=$APP_ID
Terminal=$terminal
Categories=Utility;
Keywords=vg-resource;models;sprites;textures;download;
StartupNotify=$terminal
EOF
    chmod 755 "$path"
}

install_entries() {
    write_entry "$GUI_ENTRY" "VG Resource Download" \
        "Download every asset of a game from The Models Resource" \
        "./download.sh --gui" "false"
    write_entry "$TUI_ENTRY" "VG Resource Download (TUI)" \
        "Download every asset of a game from The Models Resource (terminal)" \
        "./download.sh --tui" "true"
    say "Voci di menu installate in $APPS_DIR"
}

# --------------------------------------------------------------------- menu
refresh_menu() {
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$ICON_ROOT" >/dev/null 2>&1 || true
    fi
}

# --------------------------------------------------------------------- main
case "${1:-}" in
    --help|-h)
        usage
        exit 0
        ;;
    --uninstall)
        rm -f "$GUI_ENTRY" "$TUI_ENTRY"
        remove_icons
        refresh_menu
        say "Icona e voci di menu rimosse."
        exit 0
        ;;
    "")
        ;;
    *)
        err "Opzione sconosciuta: $1"
        usage >&2
        exit 2
        ;;
esac

[ -f "$HERE/download.sh" ] || { err "download.sh non trovato in $HERE"; exit 1; }

install_icons
install_entries
refresh_menu

say ""
say "Fatto. Cerca \"VG Resource Download\" nel menu delle applicazioni."
say "Per rimuovere tutto: $0 --uninstall"
