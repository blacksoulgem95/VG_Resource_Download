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
ENT_MAIN="$HERE/entitlements.plist"
ENT_NODE="$HERE/entitlements-node.plist"

# Firma i binari annidati prima del bundle: con l'hardened runtime ogni
# eseguibile e ogni libreria devono avere una firma valida *prima* che il
# bundle venga suggellato, se no macOS rifiuta l'avvio con "code signature
# invalid".
sign_nested() {
    local identity="$1"
    local count=0

    # 1. I singoli file Mach-O (binari e .dylib). find -depth li dà dal più
    #    profondo al più superficiale.
    while IFS= read -r -d '' f; do
        # Solo i Mach-O: ci sono anche .py, .txt, JSON e via dicendo.
        file -b "$f" | grep -q 'Mach-O' || continue

        # Il driver Node di Playwright ha bisogno dei permessi JIT per V8.
        local ents="$ENT_MAIN"
        case "$f" in
            */playwright/driver/node) ents="$ENT_NODE" ;;
        esac

        codesign --force --timestamp --options runtime \
            --entitlements "$ents" --sign "$identity" "$f" 2>/dev/null \
            || { say "   firma fallita: ${f#"$APP"/}"; return 1; }
        count=$((count + 1))
    done < <(find "$APP/Contents" -depth -type f -perm -u+x -print0)

    # 2. I bundle annidati (Python.framework e simili): hanno un Info.plist,
    #    quindi vanno firmati come bundle, non solo file per file.
    while IFS= read -r -d '' d; do
        codesign --force --timestamp --options runtime --deep \
            --sign "$identity" "$d" 2>/dev/null \
            || { say "   firma fallita: ${d#"$APP"/}"; return 1; }
        count=$((count + 1))
    done < <(find "$APP/Contents" -depth -type d \
                 \( -name '*.framework' -o -name '*.bundle' -o -name '*.xpc' \) -print0)

    say "   firmati $count elementi annidati"
}

sign_app() {
    local identity="${MACOS_SIGN_IDENTITY:--}"

    if [ "$identity" = "-" ]; then
        # Ad hoc: niente timestamp (non esiste un'autorità) e niente
        # entitlements, che senza un Team ID non avrebbero senso.
        say "==> Firma ad hoc"
        codesign --force --deep --sign - "$APP" \
            || die "firma ad hoc fallita"
    else
        say "==> Firma con $identity"
        sign_nested "$identity" || die "firma dei binari annidati fallita"
        codesign --force --timestamp --options runtime \
            --entitlements "$ENT_MAIN" --sign "$identity" "$APP" \
            || die "firma del bundle fallita"
    fi

    say "==> Verifica della firma"
    if ! codesign --verify --deep --strict --verbose=2 "$APP"; then
        if [ "$identity" = "-" ]; then
            die "verifica della firma fallita"
        fi
        # Rete di sicurezza: se qualche bundle annidato è rimasto fuori,
        # un --deep sul .app chiude i buchi. Non è l'ideale per Apple, ma
        # meglio un pacchetto firmato che uno rifiutato.
        say "   verifica fallita, riprovo con una firma --deep del bundle"
        codesign --force --timestamp --options runtime --deep \
            --entitlements "$ENT_MAIN" --sign "$identity" "$APP" \
            || die "firma --deep del bundle fallita"
        codesign --verify --deep --strict --verbose=2 "$APP" \
            || die "verifica della firma fallita anche dopo --deep"
    fi
}

sign_file() {
    local identity="${MACOS_SIGN_IDENTITY:--}"
    [ "$identity" = "-" ] && return 0
    codesign --force --timestamp --sign "$identity" "$1" \
        || say "avviso: firma di $1 fallita"
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

# Firma anche il DMG: Gatekeeper controlla la firma del contenitore prima di
# montarlo, e notarytool accetta più facilmente un DMG già firmato.
sign_file "$OUT"

notarize "$OUT"

say ""
say "Fatto: $OUT  ($(du -h "$OUT" | cut -f1))"
