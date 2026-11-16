#!/usr/bin/env python3
"""
Scarica tutti gli asset di una pagina gioco di The Models Resource
(models.spriters-resource.com) aggirando il challenge JavaScript di Cloudflare.

Cloudflare blocca curl/python-requests con un 403 "Just a moment...", quindi il
lavoro viene fatto da un vero Chrome (Playwright): il browser supera il
challenge, conserva il cookie `cf_clearance` e i download passano dal suo
contesto HTTP autenticato.

Uso:
    interfaccia grafica: vg_gui.py
    interfaccia a testo:  vg_tui.py
    riga di comando:     vg_download.py <url> [opzioni]

Launcher inclusi:
    download.sh            Linux
    download-macos.command macOS (doppio clic dal Finder)
    download.bat           Windows

Opzioni principali:
    -o, --out DIR      cartella di destinazione (default: nome del gioco)
    --delay SECONDI    pausa tra un download e l'altro (default 0.5)
    --force            riscarica anche i file già presenti
    --profile DIR      profilo Chrome persistente (default .chrome-profile)
    --headless         prova senza finestra (di solito Cloudflare blocca)
    --limit N          scarica solo i primi N asset (utile per provare)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from html import unescape as unescape_html
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "verifying you are human",
    "checking your browser",
    "un momento",
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate",
]

# Ogni asset nella pagina gioco: <a href=".../asset/123/" class="iconlink"> ... </a>
ANCHOR_RE = re.compile(r'<a\b([^>]*class="[^"]*\biconlink\b[^"]*"[^>]*)>(.*?)</a>', re.S)
HREF_RE = re.compile(r'href="([^"]+)"')
HEADER_RE = re.compile(r'class="iconheader"[^>]*title="([^"]*)"')
ALT_RE = re.compile(r'<img[^>]*alt="([^"]*)"')
IMG_RE = re.compile(r'<img[^>]*src="([^"]+)"')
SECTION_RE = re.compile(r'<span class="asset-count">\[\d+\]</span>\s*([^<]+)')
ICON_PATH_RE = re.compile(r"/media/asset_icons/(\d+)/(\d+)\.png")
ASSET_HREF_RE = re.compile(r"/(?:[^/]+)/(?:[^/]+)/asset/(\d+)/")


def log(msg: str = "") -> None:
    print(msg, flush=True)


def find_chrome() -> str | None:
    """Trova Chrome/Chromium/Edge/Brave sul sistema (Linux, macOS, Windows)."""
    env = os.environ.get("VG_CHROME") or os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env

    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "brave-browser",
        "microsoft-edge",
        "msedge",
    ):
        path = shutil.which(name)
        if path:
            return path

    candidates: list[str] = []
    if sys.platform == "darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            str(Path.home()
                / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    elif os.name == "nt":
        roots = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        relatives = [
            r"Google\Chrome\Application\chrome.exe",
            r"Chromium\Application\chrome.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
            r"Microsoft\Edge\Application\msedge.exe",
        ]
        for root in roots:
            if not root:
                continue
            for rel in relatives:
                candidates.append(str(Path(root) / rel))

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def normalize_game_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise SystemExit("Errore: nessun URL inserito.")
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parts = urlsplit(raw)
    path = parts.path
    # Se l'utente incolla la pagina di un singolo asset, si risale al gioco.
    path = re.sub(r"/asset/\d+/?$", "/", path)
    if not path.endswith("/"):
        path += "/"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def page_ready(page) -> bool:
    try:
        title = (page.title() or "").strip()
    except Exception:
        return False
    if not title:
        return False
    low = title.lower()
    return not any(marker in low for marker in CHALLENGE_MARKERS)


def fetch_html(page, url: str, label: str, attempts: int = 4, wait: int = 90):
    """Naviga finché Cloudflare non lascia passare e restituisce (titolo, html)."""
    for attempt in range(1, attempts + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:  # navigazione interrotta dal reload del challenge
            log(f"   [{label}] navigazione: {exc.__class__.__name__}, riprovo...")

        deadline = time.time() + wait
        while time.time() < deadline:
            page.wait_for_timeout(1000)
            if not page_ready(page):
                continue
            try:
                page.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception:
                pass
            for _ in range(12):
                try:
                    return page.title(), page.content()
                except Exception:
                    page.wait_for_timeout(500)
            break

        log(f"   [{label}] tentativo {attempt}/{attempts}: Cloudflare non ancora superato")
        time.sleep(2 + attempt)

    raise RuntimeError(
        "Cloudflare non ha lasciato passare la pagina.\n"
        "Suggerimenti: riprova tra qualche minuto, oppure apri il sito a mano\n"
        "nel Chrome che si è appena aperto (a volte serve un clic sul check)."
    )


def extract_title(html: str) -> str:
    match = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", html, re.S)
    if not match:
        return ""
    return unescape_html(re.sub(r"<[^>]+>", "", match.group(1))).strip()


def extract_assets(html: str) -> list[dict]:
    """Restituisce [{'id','name','section','page_url','zip_url'}, ...]."""
    sections = []
    for match in SECTION_RE.finditer(html):
        sections.append((match.start(), match.group(1).strip()))

    def section_at(pos: int) -> str:
        name = ""
        for start, text in sections:
            if start <= pos:
                name = text
            else:
                break
        return name

    assets: list[dict] = []
    seen: set[str] = set()

    for match in ANCHOR_RE.finditer(html):
        attrs, body = match.group(1), match.group(2)
        href_match = HREF_RE.search(attrs)
        if not href_match:
            continue
        page_path = href_match.group(1)
        id_match = ASSET_HREF_RE.search(page_path)
        if not id_match:
            continue
        asset_id = id_match.group(1)
        if asset_id in seen:
            continue
        seen.add(asset_id)

        header_match = HEADER_RE.search(body)
        alt_match = ALT_RE.search(body)
        if header_match:
            name = header_match.group(1).strip()
        elif alt_match:
            # gli alt sono tipo "Goofy - Kingdom Hearts II": tolgo il nome gioco
            name = re.sub(r"\s+-\s+[^-]*$", "", alt_match.group(1)).strip()
        else:
            name = f"asset_{asset_id}"
        name = unescape_html(name)

        img_match = IMG_RE.search(body)
        zip_url = ""
        if img_match:
            icon = ICON_PATH_RE.search(img_match.group(1))
            if icon:
                bucket, icon_id = icon.group(1), icon.group(2)
                zip_url = f"/media/assets/{bucket}/{icon_id}.zip"

        assets.append(
            {
                "id": asset_id,
                "name": name or f"asset_{asset_id}",
                "section": section_at(match.start()),
                "page_path": page_path,
                "zip_path": zip_url,
            }
        )

    return assets


def safe_name(text: str, max_len: int = 120) -> str:
    text = text.replace("/", "-").replace("\\", "-")
    text = re.sub(r'[<>:"|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = "asset"
    return text[:max_len].strip(" .")


def folder_name(title: str) -> str:
    cleaned = re.sub(r"[^\w .-]", "", title, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "VG_Resource_Download"


def download_zip(ctx, zip_url: str, dest: Path, referer: str) -> tuple[bool, str]:
    try:
        response = ctx.request.get(
            zip_url,
            headers={"Referer": referer, "Accept": "*/*"},
            timeout=180000,
        )
    except Exception as exc:
        return False, f"errore di rete ({exc.__class__.__name__})"

    if response.status != 200:
        return False, f"HTTP {response.status}"

    body = response.body()
    if not body:
        return False, "risposta vuota"

    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(body)
    os.replace(tmp, dest)
    return True, f"{len(body) / 1024:.0f} KB"


def asset_zip_from_page(page, asset_url: str) -> str:
    """Piano B: apre la pagina dell'asset e legge il link .zip."""
    _, html = fetch_html(page, asset_url, "asset")
    match = re.search(r'href="(/media/assets/[^"]+\.zip[^"]*)"', html)
    return urljoin(asset_url, match.group(1)) if match else ""


def run_download(
    game_url: str,
    out: str | None = None,
    delay: float = 0.5,
    force: bool = False,
    limit: int = 0,
    profile: str = ".chrome-profile",
    headless: bool = False,
    on_line=None,
    on_progress=None,
    on_out_dir=None,
) -> int:
    """Scarica tutti gli asset del gioco indicato. Restituisce un exit code.

    Callback opzionali (usati dalla GUI):
        on_line(testo)                    una riga di log
        on_progress(fatti, totali, nome, stato)  stato: start/ok/skip/fail
        on_out_dir(percorso)              cartella di destinazione risolta
    """

    def emit(msg: str = "", progress=None) -> None:
        if on_line is not None:
            on_line(msg)
        else:
            log(msg)
        if on_progress is not None and progress is not None:
            on_progress(*progress)

    game_url = normalize_game_url(game_url)
    parts = urlsplit(game_url)
    base = f"{parts.scheme}://{parts.netloc}"

    from playwright.sync_api import sync_playwright

    chrome = find_chrome()

    with sync_playwright() as pw:
        launch_opts = dict(
            headless=headless,
            args=CHROME_ARGS,
            viewport={"width": 1280, "height": 860},
            locale="en-US",
            accept_downloads=True,
        )
        if chrome and not os.environ.get("VG_FORCE_BUNDLED"):
            launch_opts["executable_path"] = chrome
        else:
            launch_opts["channel"] = "chrome"

        try:
            ctx = pw.chromium.launch_persistent_context(profile, **launch_opts)
        except Exception as exc:
            emit(f"Avvio Chrome non riuscito ({exc}).")
            emit("Installa Google Chrome oppure imposta VG_CHROME=/percorso/chrome")
            return 1

        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        try:
            emit("Apro la pagina del gioco (se compare una finestra Chrome, non chiuderla)...")
            title, html = fetch_html(page, game_url, "gioco")
            assets = extract_assets(html)
            game_title = extract_title(html) or (
                title.split(" - ")[0].strip() or "VG_Resource_Download"
            )

            if not assets:
                emit(f"ERRORE: nessun asset trovato (HTML {len(html)} caratteri).")
                return 1

            if limit and limit > 0:
                assets = assets[:limit]

            out_dir = Path(os.path.expanduser(out)) if out else Path(folder_name(game_title))
            out_dir.mkdir(parents=True, exist_ok=True)
            if on_out_dir is not None:
                on_out_dir(str(out_dir.resolve()))

            emit(f"Gioco: {game_title}")
            emit(f"Asset trovati: {len(assets)} -> {out_dir.resolve()}")
            if on_progress is not None:
                on_progress(0, len(assets), game_title, "start")
            emit()

            width = len(str(len(assets)))
            used_names: dict[str, int] = {}
            failures: list[tuple[str, str]] = []
            skipped = 0

            for index, asset in enumerate(assets, start=1):
                label = asset["name"]
                stem = safe_name(label)
                if stem in used_names:
                    used_names[stem] += 1
                    stem = f"{stem} [{asset['id']}]"
                else:
                    used_names[stem] = 1
                dest = out_dir / f"{stem}.zip"

                prefix = f"[{index:>{width}}/{len(assets)}]"
                name = label if len(label) <= 34 else label[:31] + "..."
                if dest.exists() and dest.stat().st_size > 0 and not force:
                    skipped += 1
                    emit(f"{prefix} {name:<34}  salto (già presente)",
                         (index, len(assets), label, "skip"))
                    continue

                zip_url = urljoin(base, asset["zip_path"]) if asset["zip_path"] else ""
                asset_url = urljoin(base, asset["page_path"])

                ok, info = (False, "nessun link .zip nella pagina del gioco")
                for attempt in range(1, 3):
                    if zip_url:
                        ok, info = download_zip(ctx, zip_url, dest, game_url)
                    if ok:
                        break
                    emit(f"{prefix} {name:<34}  tentativo {attempt} fallito ({info})")
                    # Il cookie di Cloudflare può essere scaduto: lo rinfresco.
                    try:
                        fetch_html(page, game_url, "refresh")
                    except Exception:
                        pass
                    if not zip_url:
                        try:
                            zip_url = asset_zip_from_page(page, asset_url)
                        except Exception:
                            zip_url = ""
                    time.sleep(2)

                if ok:
                    emit(f"{prefix} {name:<34}  OK  {info}",
                         (index, len(assets), label, "ok"))
                else:
                    emit(f"{prefix} {name:<34}  FALLITO ({info})",
                         (index, len(assets), label, "fail"))
                    failures.append((label, info))

                if delay:
                    time.sleep(delay)

            emit()
            done = len(assets) - len(failures) - skipped
            emit(
                f"Completato: {done} scaricati, {skipped} già presenti, "
                f"{len(failures)} falliti su {len(assets)} asset."
            )
            emit(f"Cartella: {out_dir.resolve()}")
            if failures:
                emit(f"Non scaricati ({len(failures)}):")
                for label, reason in failures:
                    emit(f"  - {label}: {reason}")
                return 2
            return 0

        except RuntimeError as exc:
            emit(f"ERRORE: {exc}")
            return 1
        except KeyboardInterrupt:
            emit("Interrotto dall'utente.")
            return 130
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scarica gli asset di un gioco da The Models Resource."
    )
    parser.add_argument("url", nargs="?", help="URL della pagina del gioco")
    parser.add_argument("-o", "--out", help="cartella di destinazione")
    parser.add_argument("--delay", type=float, default=0.5, help="pausa tra i download (s)")
    parser.add_argument("--force", action="store_true", help="riscarica file esistenti")
    parser.add_argument("--profile", default=".chrome-profile", help="profilo Chrome")
    parser.add_argument("--headless", action="store_true", help="avvia Chrome senza finestra")
    parser.add_argument("--limit", type=int, default=0, help="scarica solo i primi N asset")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    raw_url = args.url or input("Incolla il link completo della pagina del gioco: ")
    return run_download(
        raw_url,
        out=args.out,
        delay=args.delay,
        force=args.force,
        limit=args.limit,
        profile=args.profile,
        headless=args.headless,
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
