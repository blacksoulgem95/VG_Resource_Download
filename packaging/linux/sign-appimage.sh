#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Firma gli AppImage con GPG (firma staccata .asc) e pubblica la chiave
# pubblica, così chi scarica può verificare l'autore del file.
#
#   GPG_PRIVATE_KEY="$(cat chiave.asc)" GPG_PASSPHRASE=... \
#       ./packaging/linux/sign-appimage.sh
#
# Senza GPG_PRIVATE_KEY non fa nulla ed esce con 0: le build locali e le pull
# request restano verdi, la release senza segreto semplicemente non è firmata.
#
# Chi scarica verifica così:
#   gpg --import GPG-KEY.asc
#   gpg --verify VG_Resource_Download-1.0.0-x86_64.AppImage.asc \
#                 VG_Resource_Download-1.0.0-x86_64.AppImage
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DIST="$ROOT/dist"

say() { printf '%s\n' "$*"; }
die() { printf 'ERRORE: %s\n' "$*" >&2; exit 1; }

if [ -z "${GPG_PRIVATE_KEY:-}" ]; then
    say "Nessuna GPG_PRIVATE_KEY: AppImage lasciata non firmata."
    exit 0
fi

command -v gpg >/dev/null 2>&1 || die "gpg non installato"

KEYFILE="$(mktemp)"
trap 'rm -f "$KEYFILE" "$KEYFILE.pub"' EXIT

# La chiave arriva come testo (armored) in una variabile d'ambiente.
printf '%s' "$GPG_PRIVATE_KEY" > "$KEYFILE"

say "==> Importo la chiave GPG"
gpg --batch --import "$KEYFILE" 2>/dev/null || die "import della chiave fallito"

# --pinentry-mode loopback: senza terminale, gpg altrimenti cerca un agente
# grafico e la firma resta appesa fino al timeout del job.
SIGN_ARGS=(--batch --yes --armor --detach-sign --pinentry-mode loopback)
if [ -n "${GPG_PASSPHRASE:-}" ]; then
    SIGN_ARGS+=(--passphrase "$GPG_PASSPHRASE")
fi

shopt -s nullglob
IMAGES=("$DIST"/*.AppImage)
[ ${#IMAGES[@]} -gt 0 ] || die "nessun AppImage da firmare in $DIST"

for img in "${IMAGES[@]}"; do
    say "==> Firmo $(basename "$img")"
    gpg "${SIGN_ARGS[@]}" "$img" || die "firma fallita per $img"

    # Verifica: se la firma non torna, meglio saperlo subito che a release
    # pubblicata.
    gpg --verify "$img.asc" "$img" 2>/dev/null || die "verifica fallita per $img"
done

say "==> Esporto la chiave pubblica"
gpg --batch --armor --export > "$DIST/GPG-KEY.asc" 2>/dev/null \
    || say "avviso: esportazione della chiave pubblica fallita"

say ""
say "Fatto: ${#IMAGES[@]} AppImage firmati"
