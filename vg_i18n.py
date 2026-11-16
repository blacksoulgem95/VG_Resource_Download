#!/usr/bin/env python3
"""
Traduzioni (italiano, inglese, francese) e scelta della lingua.

La lingua attiva si sceglie in questo ordine di priorità:

    1. argomento --lang it|en|fr
    2. variabile d'ambiente VG_LANG
    3. scelta salvata dall'utente (settings.json nella cartella di configurazione)
    4. lingua di sistema (LC_ALL / LC_MESSAGES / LANG / LANGUAGE)
    5. italiano

La GUI e la TUI salvano la scelta quando l'utente cambia lingua, così viene
ricordata al lancio successivo.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_LANG = "it"

# (codice, nome nella lingua stessa) — l'ordine è quello mostrato nei selettori.
LANGUAGES: list[tuple[str, str]] = [
    ("it", "Italiano"),
    ("en", "English"),
    ("fr", "Français"),
]

LANG_CODES: list[str] = [code for code, _ in LANGUAGES]

# ---------------------------------------------------------------------------
# Testi
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------------ it --
    "it": {
        # motore di download (vg_download.py)
        "label.game": "gioco",
        "label.asset": "asset",
        "label.refresh": "aggiornamento",
        "err.no_url": "Errore: nessun URL inserito.",
        "log.nav_retry": "   [{label}] navigazione: {exc}, riprovo...",
        "log.cf_attempt": (
            "   [{label}] tentativo {attempt}/{attempts}: "
            "Cloudflare non ancora superato"
        ),
        "err.cloudflare": (
            "Cloudflare non ha lasciato passare la pagina.\n"
            "Suggerimenti: riprova tra qualche minuto, oppure apri il sito a mano\n"
            "nel Chrome che si è appena aperto (a volte serve un clic sul check)."
        ),
        "err.chrome_launch": "Avvio Chrome non riuscito ({exc}).",
        "err.chrome_hint": "Installa Google Chrome oppure imposta VG_CHROME=/percorso/chrome",
        "log.opening": (
            "Apro la pagina del gioco "
            "(se compare una finestra Chrome, non chiuderla)..."
        ),
        "err.no_assets": "ERRORE: nessun asset trovato (HTML {size} caratteri).",
        "log.game": "Gioco: {title}",
        "log.found_sections": "Asset trovati: {count} in {sections} sezioni -> {dir}",
        "log.found": "Asset trovati: {count} -> {dir}",
        "log.skip": "salto (già presente)",
        "log.attempt_failed": "tentativo {attempt} fallito ({info})",
        "log.ok": "OK",
        "log.failed": "FALLITO",
        "err.no_zip": "nessun link .zip nella pagina del gioco",
        "log.summary": (
            "Completato: {done} scaricati, {skipped} già presenti, "
            "{failed} falliti su {total} asset."
        ),
        "log.folder": "Cartella: {dir}",
        "log.failures": "Non scaricati ({count}):",
        "log.failure_line": "  - {label}: {reason}",
        "err.generic": "ERRORE: {exc}",
        "log.interrupted": "Interrotto dall'utente.",
        "err.network": "errore di rete ({exc})",
        "err.empty": "risposta vuota",
        # riga di comando (argparse)
        "cli.desc": "Scarica gli asset di un gioco da The Models Resource.",
        "cli.url": "URL della pagina del gioco",
        "cli.out": "cartella di destinazione",
        "cli.delay": "pausa tra i download (s)",
        "cli.force": "riscarica i file esistenti",
        "cli.profile": "profilo Chrome",
        "cli.headless": "avvia Chrome senza finestra",
        "cli.limit": "scarica solo i primi N asset",
        "cli.flat": "senza sottocartelle per sezione (tutti gli zip insieme)",
        "cli.lang": "lingua dell'interfaccia: it, en, fr",
        "cli.help": "mostra questo aiuto ed esce",
        "cli.group_args": "argomenti",
        "cli.group_options": "opzioni",
        "cli.prompt": "Incolla il link completo della pagina del gioco: ",
        # interfaccia grafica (vg_gui.py)
        "gui.subtitle": "Scarica tutti gli asset di un gioco da The Models Resource.",
        "gui.url_label": "Link della pagina del gioco",
        "gui.url_hint": "Es. https://models.spriters-resource.com/playstation_2/kh2/",
        "gui.dest_label": "Cartella di destinazione",
        "gui.browse": "Sfoglia...",
        "gui.dest_hint": (
            "Lascia vuoto per usare download/<Gioco>, "
            "con una sottocartella per sezione."
        ),
        "gui.overwrite": "Sovrascrivi i file già scaricati",
        "gui.start": "Avvia download",
        "gui.running": "Download in corso...",
        "gui.open_folder": "Apri cartella",
        "gui.ready": "Pronto.",
        "gui.starting": "Avvio...",
        "gui.progress": "{done}/{total} - {label}",
        "gui.progress_word": "{done}/{total} - {word}: {label}",
        "gui.word.ok": "scaricato",
        "gui.word.skip": "già presente",
        "gui.word.fail": "fallito",
        "gui.done": "Completato.",
        "gui.interrupted": "Interrotto.",
        "gui.partial": "Completato con alcuni errori (vedi log).",
        "gui.errors": "Terminato con errori (vedi log).",
        "gui.confirm_close": "Un download è in corso. Chiudere comunque?",
        "gui.need_url": "Inserisci il link della pagina del gioco.",
        "gui.invalid_url": "Il link inserito non è valido.",
        "gui.choose_dest": "Scegli la cartella di destinazione",
        "gui.lang_label": "Lingua",
        "gui.unexpected": "ERRORE imprevisto: {exc}",
        "gui.tk_missing": (
            "tkinter non è disponibile in questo Python.\n"
            "\n"
            "tkinter non è un pacchetto pip (fa parte della standard library):\n"
            "va fornito dal Python di sistema. Il launcher download.sh prova a\n"
            "prepararne una copia locale in .tk-bundle senza sudo; qui trovi le\n"
            "alternative manuali:\n"
            "\n"
            "  Debian/Ubuntu:  sudo apt install python3-tk\n"
            "  Fedora:         sudo dnf install python3-tkinter\n"
            "  Arch:           sudo pacman -S tk\n"
            "  macOS:          usa il Python di python.org (include Tk)\n"
            "                  oppure: brew install python-tk\n"
            "  Windows:        reinstallando Python spunta \"tcl/tk\"\n"
            "\n"
            "Nel frattempo puoi usare la versione a terminale: python vg_tui.py"
        ),
        # interfaccia a terminale (vg_tui.py)
        "tui.url_label": "Link della pagina del gioco",
        "tui.url_hint": "  incolla l'URL della pagina del gioco",
        "tui.dest_label": "Cartella di destinazione",
        "tui.dest_hint": "  vuoto = download/<Gioco>, sottocartelle per sezione",
        "tui.placeholder_url": "https://models.spriters-resource.com/...",
        "tui.placeholder_dest": "(vuoto = download/<Gioco>/<Sezione>)",
        "tui.overwrite": "Sovrascrivi i file già scaricati",
        "tui.start": "Avvia download",
        "tui.lang_label": "Lingua",
        "tui.hint": "Tab/frecce: sposta   Invio: avvia   Esc: esci",
        "tui.err_need_url": "Inserisci prima l'URL della pagina del gioco.",
        "tui.err_need_url2": "Inserisci l'URL della pagina del gioco.",
        "tui.plain_url": "Link della pagina del gioco: ",
        "tui.plain_dest": "Cartella di destinazione (vuoto = download/<Gioco>): ",
        "tui.plain_overwrite": "Sovrascrivere i file già presenti? [s/N] ",
        "tui.plain_no_url": "Errore: nessun URL inserito.",
        "tui.cancelled": "Annullato.",
        "tui.invalid_url": "Errore: URL non valido.",
        "tui.game": "Gioco: {value}",
        "tui.dest": "Destinazione: {value}",
        "tui.dest_auto": (
            "Destinazione: automatica (download/<Gioco>, "
            "sottocartelle per sezione)"
        ),
        "tui.overwrite_state": "Sovrascrivi esistenti: {value}",
        "tui.yes": "sì",
        "tui.no": "no",
        "tui.press_enter": "Premi Invio per chiudere...",
    },
    # ------------------------------------------------------------------ en --
    "en": {
        "label.game": "game",
        "label.asset": "asset",
        "label.refresh": "refresh",
        "err.no_url": "Error: no URL provided.",
        "log.nav_retry": "   [{label}] navigation: {exc}, retrying...",
        "log.cf_attempt": (
            "   [{label}] attempt {attempt}/{attempts}: "
            "Cloudflare has not let us through yet"
        ),
        "err.cloudflare": (
            "Cloudflare did not let the page through.\n"
            "Tips: retry in a few minutes, or open the site by hand\n"
            "in the Chrome window that just opened (a click on the checkbox\n"
            "sometimes helps)."
        ),
        "err.chrome_launch": "Could not start Chrome ({exc}).",
        "err.chrome_hint": "Install Google Chrome or set VG_CHROME=/path/to/chrome",
        "log.opening": (
            "Opening the game page "
            "(if a Chrome window appears, do not close it)..."
        ),
        "err.no_assets": "ERROR: no assets found (HTML {size} characters).",
        "log.game": "Game: {title}",
        "log.found_sections": "Assets found: {count} in {sections} sections -> {dir}",
        "log.found": "Assets found: {count} -> {dir}",
        "log.skip": "skipped (already present)",
        "log.attempt_failed": "attempt {attempt} failed ({info})",
        "log.ok": "OK",
        "log.failed": "FAILED",
        "err.no_zip": "no .zip link on the game page",
        "log.summary": (
            "Done: {done} downloaded, {skipped} already present, "
            "{failed} failed out of {total} assets."
        ),
        "log.folder": "Folder: {dir}",
        "log.failures": "Not downloaded ({count}):",
        "log.failure_line": "  - {label}: {reason}",
        "err.generic": "ERROR: {exc}",
        "log.interrupted": "Interrupted by user.",
        "err.network": "network error ({exc})",
        "err.empty": "empty response",
        "cli.desc": "Download a game's assets from The Models Resource.",
        "cli.url": "URL of the game page",
        "cli.out": "destination folder",
        "cli.delay": "pause between downloads (s)",
        "cli.force": "re-download existing files",
        "cli.profile": "Chrome profile",
        "cli.headless": "start Chrome without a window",
        "cli.limit": "download only the first N assets",
        "cli.flat": "no per-section subfolders (all zips together)",
        "cli.lang": "interface language: it, en, fr",
        "cli.help": "show this help message and exit",
        "cli.group_args": "arguments",
        "cli.group_options": "options",
        "cli.prompt": "Paste the full URL of the game page: ",
        "gui.subtitle": "Download every asset of a game from The Models Resource.",
        "gui.url_label": "Game page link",
        "gui.url_hint": "E.g. https://models.spriters-resource.com/playstation_2/kh2/",
        "gui.dest_label": "Destination folder",
        "gui.browse": "Browse...",
        "gui.dest_hint": (
            "Leave empty to use download/<Game>, "
            "with one subfolder per section."
        ),
        "gui.overwrite": "Overwrite files already downloaded",
        "gui.start": "Start download",
        "gui.running": "Download in progress...",
        "gui.open_folder": "Open folder",
        "gui.ready": "Ready.",
        "gui.starting": "Starting...",
        "gui.progress": "{done}/{total} - {label}",
        "gui.progress_word": "{done}/{total} - {word}: {label}",
        "gui.word.ok": "downloaded",
        "gui.word.skip": "already present",
        "gui.word.fail": "failed",
        "gui.done": "Completed.",
        "gui.interrupted": "Interrupted.",
        "gui.partial": "Completed with some errors (see log).",
        "gui.errors": "Finished with errors (see log).",
        "gui.confirm_close": "A download is running. Close anyway?",
        "gui.need_url": "Please enter the game page link.",
        "gui.invalid_url": "The link you entered is not valid.",
        "gui.choose_dest": "Choose the destination folder",
        "gui.lang_label": "Language",
        "gui.unexpected": "Unexpected ERROR: {exc}",
        "gui.tk_missing": (
            "tkinter is not available in this Python.\n"
            "\n"
            "tkinter is not a pip package (it is part of the standard library):\n"
            "it has to come from the system Python. The download.sh launcher\n"
            "tries to prepare a local copy in .tk-bundle without sudo; here are\n"
            "the manual alternatives:\n"
            "\n"
            "  Debian/Ubuntu:  sudo apt install python3-tk\n"
            "  Fedora:         sudo dnf install python3-tkinter\n"
            "  Arch:           sudo pacman -S tk\n"
            "  macOS:          use the python.org Python (ships with Tk)\n"
            "                  or: brew install python-tk\n"
            "  Windows:        re-run the Python installer and tick \"tcl/tk\"\n"
            "\n"
            "In the meantime you can use the terminal version: python vg_tui.py"
        ),
        "tui.url_label": "Game page link",
        "tui.url_hint": "  paste the URL of the game page",
        "tui.dest_label": "Destination folder",
        "tui.dest_hint": "  empty = download/<Game>, subfolder per section",
        "tui.placeholder_url": "https://models.spriters-resource.com/...",
        "tui.placeholder_dest": "(empty = download/<Game>/<Section>)",
        "tui.overwrite": "Overwrite files already downloaded",
        "tui.start": "Start download",
        "tui.lang_label": "Language",
        "tui.hint": "Tab/arrows: move   Enter: start   Esc: quit",
        "tui.err_need_url": "Please enter the game page URL first.",
        "tui.err_need_url2": "Please enter the game page URL.",
        "tui.plain_url": "Game page link: ",
        "tui.plain_dest": "Destination folder (empty = download/<Game>): ",
        "tui.plain_overwrite": "Overwrite existing files? [y/N] ",
        "tui.plain_no_url": "Error: no URL provided.",
        "tui.cancelled": "Cancelled.",
        "tui.invalid_url": "Error: invalid URL.",
        "tui.game": "Game: {value}",
        "tui.dest": "Destination: {value}",
        "tui.dest_auto": (
            "Destination: automatic (download/<Game>, subfolder per section)"
        ),
        "tui.overwrite_state": "Overwrite existing: {value}",
        "tui.yes": "yes",
        "tui.no": "no",
        "tui.press_enter": "Press Enter to close...",
    },
    # ------------------------------------------------------------------ fr --
    "fr": {
        "label.game": "jeu",
        "label.asset": "asset",
        "label.refresh": "actualisation",
        "err.no_url": "Erreur : aucun URL saisi.",
        "log.nav_retry": "   [{label}] navigation : {exc}, nouvel essai...",
        "log.cf_attempt": (
            "   [{label}] tentative {attempt}/{attempts} : "
            "Cloudflare n'a pas encore laissé passer"
        ),
        "err.cloudflare": (
            "Cloudflare n'a pas laissé passer la page.\n"
            "Conseils : réessaie dans quelques minutes, ou ouvre le site à la\n"
            "main dans la fenêtre Chrome qui vient de s'ouvrir (un clic sur la\n"
            "case suffit parfois)."
        ),
        "err.chrome_launch": "Le démarrage de Chrome a échoué ({exc}).",
        "err.chrome_hint": "Installe Google Chrome ou définis VG_CHROME=/chemin/vers/chrome",
        "log.opening": (
            "J'ouvre la page du jeu "
            "(si une fenêtre Chrome apparaît, ne la ferme pas)..."
        ),
        "err.no_assets": "ERREUR : aucune ressource trouvée (HTML de {size} caractères).",
        "log.game": "Jeu : {title}",
        "log.found_sections": (
            "Ressources trouvées : {count} dans {sections} sections -> {dir}"
        ),
        "log.found": "Ressources trouvées : {count} -> {dir}",
        "log.skip": "ignoré (déjà présent)",
        "log.attempt_failed": "tentative {attempt} échouée ({info})",
        "log.ok": "OK",
        "log.failed": "ÉCHEC",
        "err.no_zip": "aucun lien .zip dans la page du jeu",
        "log.summary": (
            "Terminé : {done} téléchargés, {skipped} déjà présents, "
            "{failed} échoués sur {total} ressources."
        ),
        "log.folder": "Dossier : {dir}",
        "log.failures": "Non téléchargés ({count}) :",
        "log.failure_line": "  - {label} : {reason}",
        "err.generic": "ERREUR : {exc}",
        "log.interrupted": "Interrompu par l'utilisateur.",
        "err.network": "erreur réseau ({exc})",
        "err.empty": "réponse vide",
        "cli.desc": "Télécharge les ressources (assets) d'un jeu depuis The Models Resource.",
        "cli.url": "URL de la page du jeu",
        "cli.out": "dossier de destination",
        "cli.delay": "pause entre les téléchargements (s)",
        "cli.force": "retélécharge les fichiers existants",
        "cli.profile": "profil Chrome",
        "cli.headless": "lance Chrome sans fenêtre",
        "cli.limit": "télécharge seulement les N premières ressources",
        "cli.flat": "pas de sous-dossiers par section (tous les zip ensemble)",
        "cli.lang": "langue de l'interface : it, en, fr",
        "cli.help": "affiche cette aide et quitte",
        "cli.group_args": "arguments",
        "cli.group_options": "options",
        "cli.prompt": "Colle le lien complet de la page du jeu : ",
        "gui.subtitle": "Télécharge toutes les ressources d'un jeu depuis The Models Resource.",
        "gui.url_label": "Lien de la page du jeu",
        "gui.url_hint": "Ex. https://models.spriters-resource.com/playstation_2/kh2/",
        "gui.dest_label": "Dossier de destination",
        "gui.browse": "Parcourir...",
        "gui.dest_hint": (
            "Laisse vide pour utiliser download/<Jeu>, "
            "avec un sous-dossier par section."
        ),
        "gui.overwrite": "Écraser les fichiers déjà téléchargés",
        "gui.start": "Lancer le téléchargement",
        "gui.running": "Téléchargement en cours...",
        "gui.open_folder": "Ouvrir le dossier",
        "gui.ready": "Prêt.",
        "gui.starting": "Démarrage...",
        "gui.progress": "{done}/{total} - {label}",
        "gui.progress_word": "{done}/{total} - {word} : {label}",
        "gui.word.ok": "téléchargé",
        "gui.word.skip": "déjà présent",
        "gui.word.fail": "échoué",
        "gui.done": "Terminé.",
        "gui.interrupted": "Interrompu.",
        "gui.partial": "Terminé avec quelques erreurs (voir le journal).",
        "gui.errors": "Terminé avec des erreurs (voir le journal).",
        "gui.confirm_close": "Un téléchargement est en cours. Fermer quand même ?",
        "gui.need_url": "Saisis le lien de la page du jeu.",
        "gui.invalid_url": "Le lien saisi n'est pas valide.",
        "gui.choose_dest": "Choisis le dossier de destination",
        "gui.lang_label": "Langue",
        "gui.unexpected": "ERREUR inattendue : {exc}",
        "gui.tk_missing": (
            "tkinter n'est pas disponible dans ce Python.\n"
            "\n"
            "tkinter n'est pas un paquet pip (il fait partie de la bibliothèque\n"
            "standard) : il doit venir du Python du système. Le lanceur\n"
            "download.sh essaie d'en préparer une copie locale dans .tk-bundle\n"
            "sans sudo ; voici les alternatives manuelles :\n"
            "\n"
            "  Debian/Ubuntu : sudo apt install python3-tk\n"
            "  Fedora :        sudo dnf install python3-tkinter\n"
            "  Arch :          sudo pacman -S tk\n"
            "  macOS :         utilise le Python de python.org (inclut Tk)\n"
            "                  ou : brew install python-tk\n"
            "  Windows :       réinstalle Python en cochant \"tcl/tk\"\n"
            "\n"
            "En attendant tu peux utiliser la version terminal : python vg_tui.py"
        ),
        "tui.url_label": "Lien de la page du jeu",
        "tui.url_hint": "  colle l'URL de la page du jeu",
        "tui.dest_label": "Dossier de destination",
        "tui.dest_hint": "  vide = download/<Jeu>, sous-dossier par section",
        "tui.placeholder_url": "https://models.spriters-resource.com/...",
        "tui.placeholder_dest": "(vide = download/<Jeu>/<Section>)",
        "tui.overwrite": "Écraser les fichiers déjà téléchargés",
        "tui.start": "Lancer le téléchargement",
        "tui.lang_label": "Langue",
        "tui.hint": "Tab/flèches : naviguer   Entrée : lancer   Échap : quitter",
        "tui.err_need_url": "Saisis d'abord l'URL de la page du jeu.",
        "tui.err_need_url2": "Saisis l'URL de la page du jeu.",
        "tui.plain_url": "Lien de la page du jeu : ",
        "tui.plain_dest": "Dossier de destination (vide = download/<Jeu>) : ",
        "tui.plain_overwrite": "Écraser les fichiers existants ? [o/N] ",
        "tui.plain_no_url": "Erreur : aucun URL saisi.",
        "tui.cancelled": "Annulé.",
        "tui.invalid_url": "Erreur : URL non valide.",
        "tui.game": "Jeu : {value}",
        "tui.dest": "Destination : {value}",
        "tui.dest_auto": (
            "Destination : automatique (download/<Jeu>, sous-dossier par section)"
        ),
        "tui.overwrite_state": "Écraser les fichiers existants : {value}",
        "tui.yes": "oui",
        "tui.no": "non",
        "tui.press_enter": "Appuie sur Entrée pour fermer...",
    },
}


# ---------------------------------------------------------------------------
# Configurazione salvata
# ---------------------------------------------------------------------------


def config_path() -> Path:
    """Percorso del file dove si ricorda la lingua scelta."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "vg-resource-download" / "settings.json"


def _read_settings() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_settings(data: dict) -> None:
    try:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def normalize_lang(value: str | None) -> str | None:
    """Accetta 'it', 'it-IT', 'it_IT', 'Italian'... e restituisce il codice."""
    if not value:
        return None
    text = value.strip().lower().replace("_", "-")
    if not text:
        return None
    short = text.split("-")[0]
    if short in LANG_CODES:
        return short
    for code, name in LANGUAGES:
        if name.lower() == text or name.lower().startswith(short):
            return code
    return None


def detect_system_language() -> str | None:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        found = normalize_lang(os.environ.get(var))
        if found:
            return found
    return None


def saved_language() -> str | None:
    return normalize_lang(_read_settings().get("lang"))


def resolve_language(explicit: str | None = None) -> str:
    """Applica l'ordine di priorità e restituisce il codice scelto."""
    return (
        normalize_lang(explicit)
        or normalize_lang(os.environ.get("VG_LANG"))
        or saved_language()
        or detect_system_language()
        or DEFAULT_LANG
    )


# ---------------------------------------------------------------------------
# Stato corrente
# ---------------------------------------------------------------------------

_current: str = resolve_language(None)


def current_language() -> str:
    return _current


def set_language(code: str | None, persist: bool = False) -> str:
    """Cambia la lingua attiva; con persist=True la ricorda per la prossima volta."""
    global _current
    _current = normalize_lang(code) or DEFAULT_LANG
    if persist:
        settings = _read_settings()
        settings["lang"] = _current
        _write_settings(settings)
    return _current


def language_name(code: str | None = None) -> str:
    """Nome della lingua nella lingua stessa ('Italiano', 'English', 'Français')."""
    code = normalize_lang(code) or _current
    for candidate, name in LANGUAGES:
        if candidate == code:
            return name
    return name_of_default()


def name_of_default() -> str:
    for candidate, name in LANGUAGES:
        if candidate == DEFAULT_LANG:
            return name
    return DEFAULT_LANG


def next_language(code: str | None = None, step: int = 1) -> str:
    """Lingua successiva/precedente nell'elenco (usato dal selettore TUI)."""
    code = normalize_lang(code) or _current
    try:
        index = LANG_CODES.index(code)
    except ValueError:
        index = 0
    return LANG_CODES[(index + step) % len(LANG_CODES)]


def t(key: str, **kwargs) -> str:
    """Traduce `key`; se manca ripiega sull'italiano e poi sulla chiave."""
    text = TRANSLATIONS.get(_current, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def apply_language_arg(argv: list[str]) -> list[str]:
    """Estrae --lang/-L da argv, imposta la lingua e restituisce argv ripulito.

    Serve a GUI e TUI, che hanno un parser di argomenti scritto a mano.
    """
    remaining: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("--lang", "-L") and index + 1 < len(argv):
            set_language(argv[index + 1])
            index += 2
            continue
        if arg.startswith("--lang="):
            set_language(arg.split("=", 1)[1])
            index += 1
            continue
        remaining.append(arg)
        index += 1
    return remaining


if __name__ == "__main__":  # piccolo aiuto per provare le traduzioni
    for code in LANG_CODES:
        set_language(code)
        print(f"--- {code} ({language_name(code)}) ---")
        print(t("gui.subtitle"))
        print(t("log.game", title="Kingdom Hearts II"))
        print(t("gui.start"), "|", t("tui.hint"))
    print()
    print("config:", config_path())
    print("lingua salvata:", saved_language() or "(nessuna)")
    print("lingua di sistema:", detect_system_language() or "(sconosciuta)")
