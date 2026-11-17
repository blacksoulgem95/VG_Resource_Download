#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Crea l'AppImage da un bundle PyInstaller già pronto.
#
#   ./packaging/linux/build-appimage.sh [dist/VGResourceDownload]
#
# Produce `dist/VG_Resource_Download-<versione>-<arch>.AppImage`.
#
# Struttura dell'AppDir:
#
#   AppDir/
#     AppRun                                 avvia usr/lib/.../vgdl
#     vg-resource-download.desktop           voce di menu
#     vg-resource-download.png               icona (512)
#     usr/lib/vg-resource-download/          il bundle onedir
#     usr/share/...                          copie per i desktop che le vogliono
#
# appimagetool viene scaricato al volo e lanciato in modalità
# `--appimage-extract-and-run`, così non serve FUSE (che manca nei container
# della CI).
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DIST="${1:-$ROOT/dist/VGResourceDownload}"

APP_ID="vg-resource-download"
APP_DIR_NAME="VGResourceDownload.AppDir"

say() { printf '%s\n' "$*"; }
die() { printf 'ERRORE: %s\n' "$*" >&2; exit 1; }

[ -d "$DIST" ] || die "bundle non trovato: $DIST (esegui prima PyInstaller)"
[ -x "$DIST/vgdl" ] || die "eseguibile non trovato in $DIST/vgdl"

VERSION="$(cd "$ROOT" && python3 -c 'import vg_version; print(vg_version.__version__)')"

# appimagetool vuole ARCH in stile Linux: x86_64 / aarch64 / armhf.
MACHINE="$(uname -m)"
case "$MACHINE" in
    x86_64|amd64)   ARCH="x86_64" ;;
    aarch64|arm64)  ARCH="aarch64" ;;
    armv7l|armhf)   ARCH="armhf" ;;
    *)              ARCH="$MACHINE" ;;
esac

APPDIR="$ROOT/dist/$APP_DIR_NAME"
say "==> Preparo $APPDIR"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" \
         "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/512x512/apps"

cp -a "$DIST" "$APPDIR/usr/lib/$APP_ID"

install -m755 "$HERE/AppRun" "$APPDIR/AppRun"
install -m644 "$HERE/$APP_ID.desktop" "$APPDIR/$APP_ID.desktop"
install -m644 "$HERE/$APP_ID.desktop" "$APPDIR/usr/share/applications/$APP_ID.desktop"

ICON="$ROOT/packaging/icons/app.png"
[ -f "$ICON" ] || ICON="$ROOT/icons/web/icon-512.png"
install -m644 "$ICON" "$APPDIR/$APP_ID.png"
install -m644 "$ICON" "$APPDIR/usr/share/icons/hicolor/512x512/apps/$APP_ID.png"
install -m644 "$ICON" "$APPDIR/.DirIcon"

# La versione nel nome della voce di menu aiuta i desktop che mostrano i
# metadati dell'AppImage.
if ! grep -q '^X-AppImage-Version=' "$APPDIR/$APP_ID.desktop"; then
    printf 'X-AppImage-Version=%s\n' "$VERSION" >> "$APPDIR/$APP_ID.desktop"
fi

OUT="$ROOT/dist/VG_Resource_Download-${VERSION}-${ARCH}.AppImage"

# --- appimagetool -----------------------------------------------------------
TOOL="${APPIMAGETOOL:-}"
if [ -z "$TOOL" ]; then
    TOOL="$ROOT/packaging/build/appimagetool-$ARCH.AppImage"
    if [ ! -x "$TOOL" ]; then
        mkdir -p "$(dirname "$TOOL")"
        URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
        say "==> Scarico appimagetool ($ARCH)"
        curl -fsSL --retry 3 -o "$TOOL" "$URL" || die "download di appimagetool fallito: $URL"
        chmod +x "$TOOL"
    fi
fi

say "==> Creo l'AppImage"
# --appimage-extract-and-run evita FUSE. NO_APPSTREAM lo tiene zitto se manca
# appstreamcli nei runner minimali.
NO_APPSTREAM=1 ARCH="$ARCH" "$TOOL" --appimage-extract-and-run \
    --no-appstream "$APPDIR" "$OUT"

chmod +x "$OUT"
say ""
say "Fatto: $OUT  ($(du -h "$OUT" | cut -f1))"
