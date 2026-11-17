#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Crea il DMG da "dist/VG Resource Download.app".
#
#   ./packaging/macos/build-dmg.sh
#
# Produce `dist/VG_Resource_Download-<versione>-<arch>.dmg`.
#
# Il DMG contiene l'app e un symlink ad /Applications, così si trascina dentro.
#
# Firma: senza un certificato Apple Developer l'app viene firmata *ad hoc*
# (`codesign -s -`). Basta a evitare i problemi di bundle non firmato, ma non
# alla quarantena: chi scarica il DMG dal browser deve fare clic destro →
# Apri la prima volta (oppure `xattr -dr com.apple.quarantine`).
# Con i segreti MACOS_CERT_P12 / MACOS_CERT_PASSWORD la firma diventa quella
# vera e, se ci sono anche le credenziali di notarizzazione, si notarizza.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

APP_NAME="VG Resource Download"
APP="$ROOT/dist/$APP_NAME.app"
VOL_NAME="VG Resource Download"

say() { printf '%s\n' "$*"; }
die() { printf 'ERRORE: %s\n' "$*" >&2; exit 1; }

[ -d "$APP" ] || die "app non trovata: $APP (esegui prima PyInstaller)"

VERSION="$(cd "$ROOT" && python3 -c 'import vg_version; print(vg_version.__version__)')"
ARCH="$(uname -m)"
case "$ARCH" in
    arm64)  ARCH_LABEL="arm64" ;;
    x86_64) ARCH_LABEL="x64" ;;
    *)      ARCH_LABEL="$ARCH" ;;
esac

OUT="$ROOT/dist/VG_Resource_Download-${VERSION}-${ARCH_LABEL}.dmg"

# --- firma ------------------------------------------------------------------
sign_app() {
    local identity="${MACOS_SIGN_IDENTITY:--}"

    # PyInstaller lascia dentro all'app decine di binari (.dylib, driver Node):
    # con la firma ad hoc va bene --deep, con un certificato vero sarebbe
    # meglio firmarli uno a uno, ma --deep qui regge.
    say "==> Firma ($([ "$identity" = "-" ] && echo "ad hoc" || echo "$identity"))"
    codesign --force --deep --timestamp=none --sign "$identity" \
        --options runtime "$APP" 2>/dev/null \
        || codesign --force --deep --sign "$identity" "$APP"
    codesign --verify --deep --strict --verbose=2 "$APP" || say "avviso: verifica firma fallita"
}

if [ -n "${MACOS_CERT_P12:-}" ]; then
    KEYCHAIN="$RUNNER_TEMP/vgdl-signing.keychain-db"
    say "==> Importo il certificato di firma"
    security create-keychain -p actions "$KEYCHAIN"
    security set-keychain-settings -lut 21600 "$KEYCHAIN"
    security unlock-keychain -p actions "$KEYCHAIN"
    echo "$MACOS_CERT_P12" | base64 --decode > "$RUNNER_TEMP/cert.p12"
    security import "$RUNNER_TEMP/cert.p12" -k "$KEYCHAIN" \
        -P "${MACOS_CERT_PASSWORD:-}" -T /usr/bin/codesign
    security list-keychains -d user -s "$KEYCHAIN" $(security list-keychains -d user | tr -d '"')
    security set-key-partition-list -S apple-tool:,apple: -k actions "$KEYCHAIN" >/dev/null
    rm -f "$RUNNER_TEMP/cert.p12"
    MACOS_SIGN_IDENTITY="$(security find-identity -v -p codesigning "$KEYCHAIN" \
        | sed -n 's/.*"\(.*\)"/\1/p' | head -n 1)"
    export MACOS_SIGN_IDENTITY
fi

sign_app

# --- notarizzazione (solo se ci sono le credenziali) ------------------------
notarize() {
    if [ -z "${MACOS_NOTARY_APPLE_ID:-}" ] || [ -z "${MACOS_NOTARY_PASSWORD:-}" ]; then
        say "==> Notarizzazione saltata (credenziali assenti)"
        return 0
    fi
    say "==> Notarizzazione"
    xcrun notarytool submit "$1" \
        --apple-id "$MACOS_NOTARY_APPLE_ID" \
        --password "$MACOS_NOTARY_PASSWORD" \
        --team-id "${MACOS_NOTARY_TEAM_ID:-}" \
        --wait || die "notarizzazione fallita"
    xcrun stapler staple "$1" || say "avviso: staple fallito"
}

# --- DMG --------------------------------------------------------------------
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

say "==> Preparo il contenuto del DMG"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

# Icona del volume: se l'icns c'è, il DMG la mostra nel Finder.
ICNS="$ROOT/packaging/icons/app.icns"
if [ -f "$ICNS" ]; then
    cp "$ICNS" "$STAGE/.VolumeIcon.icns"
    # Il pannello "Ottieni informazioni" deve poter mostrare l'icona custom.
    if command -v SetFile >/dev/null 2>&1; then
        SetFile -a C "$STAGE" 2>/dev/null \
            || SetFile -a C "$STAGE/.VolumeIcon.icns" 2>/dev/null || true
    fi
fi

say "==> Creo $OUT"
rm -f "$OUT"
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$STAGE" \
    -ov -format UDZO -imagekey zlib-level=9 \
    "$OUT" >/dev/null

# L'icona custom sta nella radice del volume: va riapplicata dopo la creazione.
if [ -f "$ICNS" ]; then
    MOUNT="$(hdiutil attach "$OUT" -nobrowse -readwrite | tail -1 | cut -f3)"
    if [ -n "$MOUNT" ] && [ -d "$MOUNT" ]; then
        cp "$ICNS" "$MOUNT/.VolumeIcon.icns" 2>/dev/null || true
        SetFile -a C "$MOUNT" 2>/dev/null || true
    fi
    hdiutil detach "$MOUNT" -quiet 2>/dev/null || true
fi

notarize "$OUT"

say ""
say "Fatto: $OUT  ($(du -h "$OUT" | cut -f1))"
