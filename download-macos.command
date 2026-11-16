#!/bin/bash
#
# Launcher per macOS: doppio clic dal Finder (estensione .command).
# Apre una finestra Terminal che prepara l'ambiente e poi lancia download.sh:
# interfaccia grafica se tkinter è disponibile, altrimenti quella a terminale.
# Se si usa la versione a terminale la finestra resta aperta alla fine così
# puoi leggere l'esito o gli errori.

cd "$(dirname "$0")" || exit 1

# Il Finder non eredita il PATH completo: aggiungiamo le posizioni tipiche
# (Homebrew su Apple Silicon e su Intel, poi i percorsi di sistema).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# fa in modo che vg_tui.py aspetti Invio prima di chiudere la finestra
export VG_PAUSE=1

if [ ! -x "./download.sh" ]; then
    chmod +x ./download.sh 2>/dev/null
fi

if [ ! -x "./download.sh" ]; then
    echo "ERRORE: download.sh non trovato o non eseguibile in $(pwd)"
    echo "Premi Invio per chiudere..."
    read -r _
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERRORE: python3 non trovato."
    echo "Installa gli strumenti da riga di comando di Apple con:"
    echo "    xcode-select --install"
    echo "oppure scarica Python da https://www.python.org/downloads/macos/"
    echo
    echo "Premi Invio per chiudere..."
    read -r _
    exit 1
fi

./download.sh "$@"
exit $?
