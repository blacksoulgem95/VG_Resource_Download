#!/usr/bin/env python3
"""
Interfaccia grafica minimale (tkinter) per vg_download.

Una sola finestra con link della pagina del gioco, cartella di destinazione
(con pulsante Sfoglia), opzione "sovrascrivi" e log del download.

Esecuzione:
    python vg_gui.py [url] [-o cartella] [--force]

Se tkinter non è disponibile (tipico su Linux senza il pacchetto python3-tk)
lo script esce con codice 3 e stampa come installarlo; i launcher
(download.sh / download.bat / download-macos.command) in quel caso aprono la
versione a terminale (vg_tui.py).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from vg_download import normalize_game_url, run_download

TITLE = "VG Resource Download"
BG = "#1e1f22"
FG = "#e6e6e6"
MUTED = "#9aa0a6"
ACCENT = "#4c9aff"
OK = "#4caf50"
ERR = "#ef5350"
ENTRY_BG = "#2b2d31"


def tk_available() -> bool:
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def open_path(path: str) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self, url: str = "", dest: str = "", overwrite: bool = False):
        super().__init__()
        self.title(TITLE)
        self.configure(bg=BG)
        self.minsize(640, 620)
        self.geometry("780x700")

        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.running = False
        self.out_dir = ""
        self._after_id: str | None = None

        self.url_var = tk.StringVar(value=url.strip())
        self.dest_var = tk.StringVar(value=dest.strip())
        self.force_var = tk.BooleanVar(value=overwrite)
        self.status_var = tk.StringVar(value="Pronto.")

        self._build_style()
        self._build_widgets()
        self.after(80, self._pump)

        if self.url_var.get():
            self.dest_entry.focus_set()
        else:
            self.url_entry.focus_set()

    # ----------------------------------------------------------- layout --
    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("TkDefaultFont", 10))
        style.configure("Muted.TLabel", foreground=MUTED, font=("TkDefaultFont", 9))
        style.configure("Title.TLabel", font=("TkDefaultFont", 15, "bold"))
        style.configure(
            "Go.TButton", font=("TkDefaultFont", 10, "bold"), padding=(16, 8),
            background=ACCENT, foreground="#ffffff", borderwidth=0,
        )
        style.map(
            "Go.TButton",
            background=[("active", "#5aa9ff"), ("disabled", "#3a4a5f")],
            foreground=[("disabled", "#93a3b5")],
        )
        style.configure("TButton", padding=(10, 6))
        style.configure(
            "TCheckbutton", background=BG, foreground=FG,
            focuscolor=BG, font=("TkDefaultFont", 10),
        )
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", FG)])
        style.configure(
            "TEntry", fieldbackground=ENTRY_BG, foreground=FG,
            insertcolor=FG, bordercolor=ENTRY_BG, lightcolor=ENTRY_BG,
            darkcolor=ENTRY_BG, padding=6,
        )
        style.configure(
            "TProgressbar", background=ACCENT, troughcolor=ENTRY_BG,
            bordercolor=ENTRY_BG, lightcolor=ACCENT, darkcolor=ACCENT,
        )

    def _build_widgets(self) -> None:
        root = ttk.Frame(self, padding=(22, 18, 22, 14))
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)

        header = ttk.Label(root, text=TITLE, style="Title.TLabel")
        header.grid(row=0, column=0, sticky="w")
        ttk.Label(
            root,
            text="Scarica tutti gli asset di un gioco da The Models Resource.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 16))

        # --- link
        ttk.Label(root, text="Link della pagina del gioco").grid(row=2, column=0, sticky="w")
        self.url_entry = ttk.Entry(root, textvariable=self.url_var)
        self.url_entry.grid(row=3, column=0, sticky="ew", pady=(4, 2))
        ttk.Label(
            root,
            text="Es. https://models.spriters-resource.com/playstation_2/kh2/",
            style="Muted.TLabel",
        ).grid(row=4, column=0, sticky="w", pady=(0, 14))

        # --- destinazione
        ttk.Label(root, text="Cartella di destinazione").grid(row=5, column=0, sticky="w")
        dest_row = ttk.Frame(root)
        dest_row.grid(row=6, column=0, sticky="ew", pady=(4, 2))
        dest_row.columnconfigure(0, weight=1)
        self.dest_entry = ttk.Entry(dest_row, textvariable=self.dest_var)
        self.dest_entry.grid(row=0, column=0, sticky="ew")
        self.browse_btn = ttk.Button(dest_row, text="Sfoglia...", command=self._browse)
        self.browse_btn.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(
            root,
            text="Lascia vuoto per usare download/<Gioco>, con una sottocartella per sezione.",
            style="Muted.TLabel",
        ).grid(row=7, column=0, sticky="w", pady=(0, 14))

        # --- opzioni + avvio
        actions = ttk.Frame(root)
        actions.grid(row=8, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            actions, text="Sovrascrivi i file già scaricati", variable=self.force_var
        ).grid(row=0, column=0, sticky="w")
        self.start_btn = ttk.Button(
            actions, text="Avvia download", style="Go.TButton", command=self._start
        )
        self.start_btn.grid(row=0, column=1, sticky="e")

        # --- progresso
        self.progress = ttk.Progressbar(root, mode="determinate", maximum=1)
        self.progress.grid(row=9, column=0, sticky="ew", pady=(16, 6))
        self.status = ttk.Label(root, textvariable=self.status_var, style="Muted.TLabel")
        self.status.grid(row=10, column=0, sticky="w")

        # --- log
        log_frame = ttk.Frame(root)
        log_frame.grid(row=11, column=0, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        root.rowconfigure(11, weight=1)

        self.log = ScrolledText(
            log_frame, height=8, wrap="word", bg=ENTRY_BG, fg=FG,
            insertbackground=FG, relief="flat", borderwidth=0,
            font=("TkFixedFont", 9), padx=10, pady=8,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.configure(state="disabled")

        footer = ttk.Frame(root)
        footer.grid(row=12, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.open_btn = ttk.Button(
            footer, text="Apri cartella", command=self._open_folder, state="disabled"
        )
        self.open_btn.grid(row=0, column=1, sticky="e")

        # scorciatoie
        self.url_entry.bind("<Return>", lambda _e: self.dest_entry.focus_set())
        self.dest_entry.bind("<Return>", lambda _e: self._start())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        if self.running:
            if not messagebox.askokcancel(
                TITLE, "Un download è in corso. Chiudere comunque?"
            ):
                return
        self.destroy()

    # ----------------------------------------------------------- azioni --
    def _browse(self) -> None:
        initial = self.dest_var.get().strip()
        initial = os.path.expanduser(initial) if initial else str(Path.home())
        chosen = filedialog.askdirectory(
            title="Scegli la cartella di destinazione",
            initialdir=initial if os.path.isdir(initial) else str(Path.home()),
        )
        if chosen:
            self.dest_var.set(chosen)

    def _append(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        self.running = running
        state = "disabled" if running else "normal"
        self.start_btn.configure(state=state, text="Download in corso..." if running else "Avvia download")
        self.browse_btn.configure(state=state)
        self.url_entry.configure(state=state)
        self.dest_entry.configure(state=state)

    def _start(self) -> None:
        if self.running:
            return

        raw_url = self.url_var.get().strip()
        if not raw_url:
            messagebox.showwarning(TITLE, "Inserisci il link della pagina del gioco.")
            self.url_entry.focus_set()
            return
        try:
            url = normalize_game_url(raw_url)
        except SystemExit:
            messagebox.showerror(TITLE, "Il link inserito non è valido.")
            return

        self.url_var.set(url)
        self.out_dir = ""
        self.open_btn.configure(state="disabled")
        self.progress.configure(value=0, maximum=1)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.status_var.set("Avvio...")
        self._set_running(True)

        dest = self.dest_var.get().strip()
        force = self.force_var.get()

        def worker() -> None:
            try:
                code = run_download(
                    url,
                    out=dest or None,
                    force=force,
                    on_line=lambda text: self.events.put(("line", text)),
                    on_progress=lambda done, total, label, status: self.events.put(
                        ("progress", done, total, label, status)
                    ),
                    on_out_dir=lambda path: self.events.put(("outdir", path)),
                )
            except Exception as exc:  # pragma: no cover - difensivo
                self.events.put(("line", f"ERRORE imprevisto: {exc}"))
                code = 1
            self.events.put(("done", code))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _open_folder(self) -> None:
        if self.out_dir and os.path.isdir(self.out_dir):
            open_path(self.out_dir)

    # --------------------------------------------------- coda eventi UI --
    def _pump(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "line":
                    if event[1]:
                        self._append(event[1])
                elif kind == "progress":
                    _, done, total, label, status = event
                    if status == "start":
                        self.progress.configure(maximum=max(1, total), value=0)
                        self.status_var.set(f"0/{total} - {label}")
                    else:
                        self.progress.configure(maximum=max(1, total), value=done)
                        word = {"ok": "scaricato", "skip": "già presente", "fail": "fallito"}
                        self.status_var.set(
                            f"{done}/{total} - {word.get(status, status)}: {label}"
                        )
                elif kind == "outdir":
                    self.out_dir = event[1]
                    self.open_btn.configure(state="normal")
                elif kind == "done":
                    self._finish(event[1])
        except queue.Empty:
            pass
        except tk.TclError:
            return
        try:
            self._after_id = self.after(80, self._pump)
        except tk.TclError:
            self._after_id = None

    def destroy(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()

    def _finish(self, code: int) -> None:
        self._set_running(False)
        if code == 0:
            self.status_var.set("Completato.")
            self.progress.configure(value=self.progress.cget("maximum"))
        elif code == 130:
            self.status_var.set("Interrotto.")
        elif code == 2:
            self.status_var.set("Completato con alcuni errori (vedi log).")
        else:
            self.status_var.set("Terminato con errori (vedi log).")
        if self.out_dir:
            self.open_btn.configure(state="normal")


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

    if not tk_available():
        print(
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
            "Nel frattempo puoi usare la versione a terminale: python vg_tui.py",
            file=sys.stderr,
        )
        return 3

    try:
        App(url, dest, overwrite).mainloop()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
