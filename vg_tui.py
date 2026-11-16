#!/usr/bin/env python3
"""
TUI minima e portatile (Linux / macOS / Windows) per vg_download.

Schermata unica con due campi (link della pagina del gioco e cartella di
destinazione) più una casella "sovrascrivi". Navigazione con Tab / frecce,
Invio per avviare, Esc per uscire.

Non usa curses né dipendenze esterne: legge i tasti in raw mode (termios su
Linux/macOS, msvcrt su Windows) e ridisegna il frame con escape ANSI.
Se stdout/stdin non sono un terminale, ripiega su semplici domande testuali.
"""

from __future__ import annotations

import codecs
import os
import re
import shutil
import sys
import unicodedata

from vg_download import normalize_game_url, run_download

TITLE = "VG Resource Download"

FRAME_UNICODE = {"tl": "\u250c", "tr": "\u2510", "bl": "\u2514", "br": "\u2518",
                 "h": "\u2500", "v": "\u2502"}
FRAME_ASCII = {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"}

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# ---------------------------------------------------------------- utilità ---


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        return _enable_windows_ansi()
    return True


def _enable_windows_ansi() -> bool:
    """Attiva il supporto escape ANSI nella console di Windows 10+."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004
        return bool(kernel32.SetConsoleMode(handle, mode.value | enable_vt))
    except Exception:
        return False


class Style:
    enabled = False

    @classmethod
    def set(cls, enabled: bool) -> None:
        cls.enabled = enabled

    @classmethod
    def _wrap(cls, code: str) -> str:
        return code if cls.enabled else ""

    @classmethod
    def reset(cls) -> str:
        return cls._wrap("\x1b[0m")

    @classmethod
    def bold(cls) -> str:
        return cls._wrap("\x1b[1m")

    @classmethod
    def dim(cls) -> str:
        return cls._wrap("\x1b[2m")

    @classmethod
    def invert(cls) -> str:
        return cls._wrap("\x1b[7m")

    @classmethod
    def cyan(cls) -> str:
        return cls._wrap("\x1b[36m")

    @classmethod
    def green(cls) -> str:
        return cls._wrap("\x1b[32m")

    @classmethod
    def red(cls) -> str:
        return cls._wrap("\x1b[31m")

    @classmethod
    def yellow(cls) -> str:
        return cls._wrap("\x1b[33m")


def vlen(text: str) -> int:
    """Larghezza visibile nel terminale, ignorando le sequenze ANSI."""
    text = ANSI_RE.sub("", text)
    total = 0
    for char in text:
        total += 2 if unicodedata.east_asian_width(char) in "WF" else 1
    return total


def clip(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if vlen(text) <= width:
        return text
    out = []
    used = 0
    for char in ANSI_RE.sub("", text):
        step = 2 if unicodedata.east_asian_width(char) in "WF" else 1
        if used + step > width:
            break
        out.append(char)
        used += step
    return "".join(out)


def terminal_width(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


# ------------------------------------------------------------ lettura tasti ---

UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"
HOME, END, DELETE, BACKSPACE = "home", "end", "delete", "backspace"
TAB, BACKTAB, ENTER, ESC, CTRL_C = "tab", "backtab", "enter", "esc", "ctrl-c"

_ESCAPE_KEYS = {
    b"[A": UP, b"[B": DOWN, b"[C": RIGHT, b"[D": LEFT,
    b"OA": UP, b"OB": DOWN, b"OC": RIGHT, b"OD": LEFT,
    b"[H": HOME, b"[F": END, b"OH": HOME, b"OF": END,
    b"[1~": HOME, b"[4~": END, b"[7~": HOME, b"[8~": END,
    b"[2~": None, b"[3~": DELETE, b"[5~": None, b"[6~": None,
    b"[Z": BACKTAB, b"[200~": None, b"[201~": None,
}

_WINDOWS_KEYS = {
    "H": UP, "P": DOWN, "K": LEFT, "M": RIGHT,
    "G": HOME, "O": END, "S": DELETE, "R": None,
    "I": None, "Q": None,
}


class PosixKeys:
    def __enter__(self) -> "PosixKeys":
        import termios
        import tty

        self._fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        return self

    def __exit__(self, *exc_info) -> bool:
        import termios

        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)
        return False

    def _byte(self, timeout: float | None = None) -> bytes:
        if timeout is not None:
            import select

            try:
                ready, _, _ = select.select([self._fd], [], [], timeout)
            except Exception:
                return b""
            if not ready:
                return b""
        try:
            return os.read(self._fd, 1)
        except OSError:
            return b""

    def read_key(self):
        raw = self._byte()
        if not raw:
            return None

        if raw == b"\x1b":
            seq = b""
            while True:
                nxt = self._byte(0.06)
                if not nxt:
                    break
                seq += nxt
                if nxt == b"~" or nxt.isalpha():
                    break
            if not seq:
                return ("key", ESC)
            return ("key", _ESCAPE_KEYS[seq]) if _ESCAPE_KEYS.get(seq) else None

        if raw in (b"\r", b"\n"):
            return ("key", ENTER)
        if raw == b"\t":
            return ("key", TAB)
        if raw in (b"\x7f", b"\x08"):
            return ("key", BACKSPACE)
        if raw == b"\x03":
            return ("key", CTRL_C)

        text = self._decoder.decode(raw)
        if not text:
            return None
        return ("char", text)


class WindowsKeys:
    def __enter__(self) -> "WindowsKeys":
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def read_key(self):
        import msvcrt

        char = msvcrt.getwch()
        if char in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            mapped = _WINDOWS_KEYS.get(code)
            return ("key", mapped) if mapped else None
        if char == "\x03":
            return ("key", CTRL_C)
        if char in ("\r", "\n"):
            return ("key", ENTER)
        if char in ("\x7f", "\x08"):
            return ("key", BACKSPACE)
        if char == "\t":
            return ("key", TAB)
        if char == "\x1b":
            return ("key", ESC)
        if char >= " ":
            return ("char", char)
        return None


def keyboard():
    return WindowsKeys() if os.name == "nt" else PosixKeys()


# ------------------------------------------------------------------- stato ---

FIELD_URL, FIELD_DEST, FIELD_FORCE, FIELD_START = range(4)


class App:
    def __init__(self, url: str = "", dest: str = "", overwrite: bool = False):
        self.values = [url.strip(), dest.strip()]
        self.cursor = [len(self.values[0]), len(self.values[1])]
        self.overwrite = bool(overwrite)
        self.focus = FIELD_URL if not self.values[0] else FIELD_DEST
        self.error = ""
        self.frame = FRAME_ASCII if os.name == "nt" else FRAME_UNICODE

    # --- editing -------------------------------------------------------
    def _field(self) -> tuple[str, int]:
        return self.values[self.focus], self.cursor[self.focus]

    def insert(self, text: str) -> None:
        value, pos = self._field()
        text = text.replace("\r", "").replace("\n", "")
        self.values[self.focus] = value[:pos] + text + value[pos:]
        self.cursor[self.focus] = pos + len(text)

    def backspace(self) -> None:
        value, pos = self._field()
        if pos > 0:
            self.values[self.focus] = value[: pos - 1] + value[pos:]
            self.cursor[self.focus] = pos - 1

    def delete(self) -> None:
        value, pos = self._field()
        if pos < len(value):
            self.values[self.focus] = value[:pos] + value[pos + 1:]

    def move_cursor(self, delta: int) -> None:
        value, pos = self._field()
        self.cursor[self.focus] = max(0, min(len(value), pos + delta))
        self.values[self.focus] = value

    def cursor_home(self) -> None:
        self.cursor[self.focus] = 0

    def cursor_end(self) -> None:
        self.cursor[self.focus] = len(self.values[self.focus])

    # --- risultato -----------------------------------------------------
    def result(self) -> dict:
        return {
            "url": self.values[FIELD_URL].strip(),
            "dest": self.values[FIELD_DEST].strip(),
            "overwrite": self.overwrite,
        }


# --------------------------------------------------------------- disegno -----


def _pad(text: str, width: int) -> str:
    text = clip(text, width)
    return text + " " * max(0, width - vlen(text))


def _field_line(app: App, index: int, width: int) -> str:
    focused = app.focus == index
    marker = ">" if focused else " "
    value = app.values[index]
    cursor = app.cursor[index]
    placeholder = (
        "https://models.spriters-resource.com/..."
        if index == FIELD_URL
        else "(vuoto = nome del gioco)"
    )

    avail = max(1, width - 4)
    if not value:
        text = clip(placeholder, avail)
        body = Style.dim() + text + Style.reset() if focused else text
        return f"  {marker} {body}"

    if len(value) <= avail:
        shown, col = value, cursor
    else:
        start = max(0, cursor - avail + 1) if cursor >= avail else 0
        shown, col = value[start:start + avail], cursor - start

    if not focused:
        return f"  {marker} {shown}"

    before, at, after = shown[:col], shown[col:col + 1] or " ", shown[col + 1:]
    block = Style.invert() + at + Style.reset() if Style.enabled else f"[{at}]"
    return f"  {marker} {before}{block}{after}"


def render(app: App) -> str:
    cols = terminal_width()
    inner = max(24, min(66, cols - 6))
    frame = app.frame
    border = Style.dim() + frame["v"] + Style.reset()

    def row(content: str = "") -> str:
        return border + " " + _pad(content, inner - 1) + border
        # nota: 1 spazio a sinistra, il resto a destra

    lines: list[str] = []

    head_title = f" {TITLE} "
    fill = inner - vlen(head_title) - 1
    if fill < 1:
        head_title, fill = " VG ", max(1, inner - 4)
    lines.append(
        frame["tl"] + frame["h"] + Style.bold() + head_title + Style.reset()
        + frame["h"] * fill + frame["tr"]
    )

    lines.append(row())
    lines.append(row(Style.bold() + "Link della pagina del gioco" + Style.reset()))
    lines.append(row(_field_line(app, FIELD_URL, inner - 1)))
    lines.append(row(Style.dim() + "  incolla l'URL della pagina del gioco" + Style.reset()))
    lines.append(row())

    lines.append(row(Style.bold() + "Cartella di destinazione" + Style.reset()))
    lines.append(row(_field_line(app, FIELD_DEST, inner - 1)))
    lines.append(row(Style.dim() + "  lascia vuoto per creare la cartella dal titolo" + Style.reset()))
    lines.append(row())

    box = "[x]" if app.overwrite else "[ ]"
    checked = (
        Style.bold() + box + Style.reset() + " Sovrascrivi i file già scaricati"
        if app.overwrite
        else Style.dim() + box + Style.reset() + Style.dim() + " Sovrascrivi i file già scaricati" + Style.reset()
    )
    if app.focus == FIELD_FORCE:
        checked = Style.invert() + f" {box} Sovrascrivi i file già scaricati " + Style.reset()
    lines.append(row("  " + checked))
    lines.append(row())

    button = "[ Avvia download ]"
    if app.focus == FIELD_START:
        button = Style.invert() + Style.bold() + "  Avvia download  " + Style.reset()
    else:
        button = Style.cyan() + Style.bold() + button + Style.reset()
    lines.append(row("  " + button))

    if app.error:
        lines.append(row(Style.red() + Style.bold() + "  " + app.error + Style.reset()))
    else:
        lines.append(row())

    hint = "Tab/frecce: sposta   Invio: avvia   Esc: esci"
    lines.append(row(Style.dim() + "  " + hint + Style.reset()))
    lines.append(frame["bl"] + frame["h"] * inner + frame["br"])

    return "\x1b[H\x1b[2J" + "\x1b[?25l" + "\n".join(lines) + "\x1b[0m"


def draw(app: App) -> None:
    sys.stdout.write(render(app))
    sys.stdout.flush()


def clear_screen() -> None:
    sys.stdout.write("\x1b[0m\x1b[?25h\x1b[H\x1b[2J")
    sys.stdout.flush()


# ------------------------------------------------------------------- TUI -----


def tui(url: str = "", dest: str = "", overwrite: bool = False) -> dict | None:
    """Esegue la TUI e restituisce {'url','dest','overwrite'} oppure None."""
    app = App(url, dest, overwrite)

    with keyboard() as keys:
        try:
            while True:
                draw(app)
                event = keys.read_key()
                if event is None:
                    continue
                kind, value = event

                if kind == "char":
                    if value == " " and app.focus == FIELD_FORCE:
                        app.overwrite = not app.overwrite
                        continue
                    if value in (" ", "\t") and app.focus == FIELD_START:
                        app.error = ""
                        if app.values[FIELD_URL].strip():
                            return app.result()
                        app.error = "Inserisci prima l'URL della pagina del gioco."
                        app.focus = FIELD_URL
                        continue
                    if app.focus in (FIELD_URL, FIELD_DEST):
                        app.insert(value)
                        app.error = ""
                    continue

                if value == CTRL_C or value == ESC:
                    return None
                if value in (TAB, DOWN):
                    app.focus = (app.focus + 1) % 4
                elif value in (BACKTAB, UP):
                    app.focus = (app.focus - 1) % 4
                elif value == ENTER:
                    app.error = ""
                    if app.focus == FIELD_FORCE:
                        app.overwrite = not app.overwrite
                    elif not app.values[FIELD_URL].strip():
                        app.error = "Inserisci l'URL della pagina del gioco."
                        app.focus = FIELD_URL
                    else:
                        return app.result()
                elif app.focus in (FIELD_URL, FIELD_DEST):
                    if value == LEFT:
                        app.move_cursor(-1)
                    elif value == RIGHT:
                        app.move_cursor(1)
                    elif value == HOME:
                        app.cursor_home()
                    elif value == END:
                        app.cursor_end()
                    elif value == BACKSPACE:
                        app.backspace()
                    elif value == DELETE:
                        app.delete()
        finally:
            clear_screen()


def ask_plain(url: str, dest: str, overwrite: bool) -> dict | None:
    """Fallback senza terminale interattivo."""
    print(f"== {TITLE} ==")
    if not url:
        try:
            url = input("Link della pagina del gioco: ").strip()
        except EOFError:
            return None
    if not dest:
        try:
            dest = input("Cartella di destinazione (vuoto = automatica): ").strip()
        except EOFError:
            dest = ""
    if not url:
        print("Errore: nessun URL inserito.")
        return None
    if not overwrite:
        try:
            answer = input("Sovrascrivere i file già presenti? [s/N] ").strip().lower()
        except EOFError:
            answer = ""
        overwrite = answer.startswith("s")
    return {"url": url, "dest": dest, "overwrite": overwrite}


def main(argv: list[str]) -> int:
    url = ""
    dest = ""
    overwrite = False

    args = list(argv)
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-o", "--out") and index + 1 < len(args):
            dest = args[index + 1]
            index += 2
            continue
        if arg.startswith("--out="):
            dest = arg.split("=", 1)[1]
        elif arg in ("-f", "--force"):
            overwrite = True
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        elif not arg.startswith("-") and not url:
            url = arg
        index += 1

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    Style.set(interactive and _supports_color())

    answers = tui(url, dest, overwrite) if interactive else ask_plain(url, dest, overwrite)
    if not answers:
        clear_screen()
        print("Annullato.")
        return 130

    try:
        target = normalize_game_url(answers["url"])
    except SystemExit:
        print("Errore: URL non valido.")
        return 1

    if interactive:
        clear_screen()
    print(f"== {TITLE} ==")
    print(f"Gioco: {target}")
    if answers["dest"]:
        print(f"Destinazione: {os.path.expanduser(answers['dest'])}")
    else:
        print("Destinazione: cartella automatica (nome del gioco)")
    print("Sovrascrivi esistenti:", "sì" if answers["overwrite"] else "no")
    print()

    code = run_download(
        target,
        out=answers["dest"] or None,
        force=answers["overwrite"],
    )

    if interactive and os.environ.get("VG_PAUSE", "1") != "0":
        print()
        try:
            input("Premi Invio per chiudere...")
        except EOFError:
            pass
    return code


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        clear_screen()
        sys.exit(130)
