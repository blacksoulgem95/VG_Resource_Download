# VG Resource Download

Scarica in automatico tutti gli asset (zip) di un gioco da
[The Models Resource](https://models.spriters-resource.com/) /
[The Spriters Resource](https://www.spriters-resource.com/) e siti gemelli.

Il sito è protetto da Cloudflare (`Just a moment...`): `curl` e `requests`
prendono sempre `403`, quindi il lavoro lo fa un vero Chrome pilotato da
[Playwright](https://playwright.dev/python/). Il browser supera il challenge,
conserva il cookie `cf_clearance` nel profilo `.chrome-profile` e i download
passano dal suo contesto HTTP autenticato.

## Installazione

Sulla pagina [Releases](https://github.com/blacksoulgem95/VG_Resource_Download/releases)
ci sono i pacchetti già pronti:

| Sistema | File | Installazione |
|---|---|---|
| Windows | `VG_Resource_Download-<ver>-x64-setup.exe` | esegui l'installer (NSIS) |
| macOS | `VG_Resource_Download-<ver>-arm64.dmg` / `-x64.dmg` | apri il DMG e trascina l'app in *Applicazioni* |
| Linux | `VG_Resource_Download-<ver>-x86_64.AppImage` | `chmod +x` e avvia |

Nulla da installare a parte: l'app usa il Chrome (o Chromium/Edge/Brave) già
presente nel sistema. In alternativa si può partire dai sorgenti con i
launcher qui sotto.

## Avvio rapido

| Sistema | Comando |
|---|---|
| Linux | `./download.sh` |
| macOS | doppio clic su `download-macos.command` (o `./download.sh`) |
| Windows | doppio clic su `download.bat` |

Il launcher prepara da solo l'ambiente Python (`.venv` + Playwright) la prima
volta, poi apre l'interfaccia grafica.

## Le tre interfacce

```bash
./download.sh                 # grafica (tkinter): URL, cartella, log, progresso
./download.sh --tui           # a terminale, a schermo intero, senza dipendenze
./download.sh <url> [...]     # riga di comando, per script e automazioni
```

Dalla GUI puoi anche scegliere la cartella con **Sfoglia...** e aprire la
cartella alla fine con **Apri cartella**.

## Lingue

L'interfaccia è disponibile in **italiano**, **inglese** e **francese**. Il
selettore **Lingua** è in alto a destra nella GUI (e nella TUI, alla voce
`Lingua`); la scelta viene ricordata nel file di configurazione
(`~/.config/vg-resource-download/settings.json`).

Si può forzare la lingua anche da riga di comando o con una variabile
d'ambiente:

```bash
./download.sh --lang fr          # oppure -L en
VG_LANG=it ./download.sh --tui
```

Senza indicazioni vale la lingua di sistema (`LANG`), con l'italiano come
ripiego. I testi stanno tutti in `vg_i18n.py`.

## Icona

L'icona è nella cartella `icons/` (pacchetto generato per web, Android e iOS):
la GUI usa `icons/web/icon-512.png` e `icon-192.png`, la TUI resta nel
terminale.

Su Linux puoi aggiungere l'icona e le voci nel menu delle applicazioni senza
sudo:

```bash
./install-desktop-icon.sh            # installa (o aggiorna)
./install-desktop-icon.sh --uninstall  # rimuove
```

Crea **VG Resource Download** (GUI) e **VG Resource Download (TUI)** nel menu.
Su macOS e Windows l'icona compare già nella finestra della GUI; per usarla
anche come icona di un collegamento basta puntare `icons/web/favicon.ico`.

### tkinter (la libreria della GUI)

`tkinter` **non è un pacchetto pip**: è un'estensione della standard library
(`_tkinter`), quindi non si può installare nel venv con `pip install`. Il venv
la vede già da solo, perché condivide la standard library del Python di sistema
(non serve `--system-site-packages`); se manca, manca a monte, nel pacchetto di
sistema del Python.

Per questo `download.sh`, se non la trova, se la prepara **senza sudo**: scarica
i pacchetti Debian con `apt-get download` e li estrae in `.tk-bundle/`, poi
punta lì `PYTHONPATH` e `LD_LIBRARY_PATH`. Su Debian/Ubuntu funziona subito; il
bundle viene riusato dalle esecuzioni successive (circa 10 MB).

Se preferisci installarla a livello di sistema (consigliato, più pulito):

- Debian/Ubuntu: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`
- Arch: `sudo pacman -S tk`
- macOS: usa il Python di python.org oppure `brew install python-tk`
- Windows: reinstalla Python spuntando "tcl/tk and IDLE"

## Riga di comando

```bash
python vg_download.py <url> [-o CARTELLA] [--flat] [--delay 0.5] [--force] [--limit N]
```

- `-o, --out` cartella del gioco (default: `download/<Gioco>`)
- `--flat` mette tutti gli zip in un'unica cartella, senza sottocartelle per sezione
- `--delay` pausa in secondi tra un file e l'altro (default `0.5`)
- `--force` riscarica anche i file già presenti
- `--limit` scarica solo i primi N asset (utile per provare)
- `--profile` profilo Chrome persistente (default `.chrome-profile`)
- `--headless` prova senza finestra (Cloudflare di solito blocca)

Si può incollare anche l'URL di un singolo asset: viene ricondotto alla pagina
del gioco.

## Dove finiscono i file

Se non scegli una cartella la destinazione è `download/<Gioco>/`, con una
sottocartella per ogni sezione della pagina del gioco:

```
download/
└── Kingdom_Hearts_II/
    ├── Sora/
    │   ├── Sora (Anti Form).zip
    │   └── Sora (Final).zip
    ├── Goofy/
    │   └── Goofy.zip
    └── Characters/
        └── ...
```

Specificando `-o` (o scegliendo la cartella nella GUI o nella TUI) quella
diventa la cartella del gioco e le sottocartelle per sezione restano. Con
`--flat` si ottiene invece la vecchia struttura piatta.

Quando l'app è installata il percorso predefinito non può stare accanto
all'eseguibile (Program Files e `/opt` sono in sola lettura), quindi diventa:

| Sistema | Download | Profilo Chrome | Impostazioni |
| --- | --- | --- | --- |
| Linux | `~/Downloads/VG Resource Download/` | `~/.local/share/vg-resource-download/chrome-profile/` | `~/.config/vg-resource-download/settings.json` |
| macOS | `~/Downloads/VG Resource Download/` | `~/Library/Application Support/vg-resource-download/chrome-profile/` | `~/Library/Application Support/vg-resource-download/settings.json` |
| Windows | `%USERPROFILE%\Downloads\VG Resource Download\` | `%LOCALAPPDATA%\vg-resource-download\chrome-profile\` | `%LOCALAPPDATA%\vg-resource-download\settings.json` |

Le variabili `VG_DOWNLOAD_DIR` e `VG_PROFILE` forzano i primi due percorsi.

## File

- `vg_download.py` – motore: parsing della pagina e download
- `vg_gui.py` – interfaccia grafica tkinter
- `vg_tui.py` – interfaccia a terminale (senza curses, portabile)
- `vg_launcher.py` – punto d'ingresso unico (`--gui`, `--tui`, CLI)
- `vg_i18n.py` – traduzioni italiano/inglese/francese
- `vg_icons.py` – icona della finestra e dell'app
- `vg_paths.py` – percorsi corretti anche da installata
- `vg_version.py` – versione e metadati, unica fonte
- `download.sh`, `download.bat`, `download-macos.command` – launcher per sistema
- `packaging/` – icone native, spec PyInstaller e script dei tre installer
- `.github/workflows/build.yml` – la pipeline che compila i pacchetti
- `.tk-bundle/` – solo se serve: copia locale di tkinter preparata da `download.sh`

## Compilare gli installer

L'app si impacchetta con **PyInstaller** in modalità *onedir* (avvio più
rapido e meno falsi positivi degli antivirus rispetto al *onefile*). I browser
di Playwright **non** vengono inclusi: si usa il Chrome installato
dall'utente, così il pacchetto resta ~65 MB compresso invece di ~400.

Serve Python 3.12 e queste dipendenze:

```bash
python -m pip install playwright pyinstaller pillow
```

### Linux → AppImage

```bash
python packaging/make_icons.py                       # icone native da icons/web/
pyinstaller --noconfirm --clean packaging/vgdl.spec  # → dist/VGResourceDownload/
bash packaging/linux/build-appimage.sh               # → dist/*.AppImage
```

`build-appimage.sh` scarica `appimagetool` in `packaging/build/` e lo esegue
con `--appimage-extract-and-run`, quindi non serve FUSE né `sudo`.
Se il Python di sistema non ha tkinter, `packaging/bootstrap-tk.sh` lo
estrae in `.tk-bundle/` senza privilegi:

```bash
eval "$(bash packaging/bootstrap-tk.sh --export)"
```

### Windows → installer NSIS

```powershell
python packaging\make_icons.py
pyinstaller --noconfirm --clean packaging\vgdl.spec
powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1
```

Serve [NSIS](https://nsis.sourceforge.io/) 3.x (`makensis`). L'installer crea
la voce nel menu Start, il collegamento sul desktop, un comando `vgdl` in
`%LOCALAPPDATA%\Microsoft\WindowsApps` (già nel PATH) e la voce in *App e
funzionalità*. Alla disinstallazione chiede se rimuovere anche i dati locali.

### macOS → DMG

```bash
python packaging/make_icons.py
pyinstaller --noconfirm --clean packaging/vgdl.spec   # → dist/VG Resource Download.app
bash packaging/macos/build-dmg.sh                     # → dist/*.dmg
```

Lo script firma l'app (ad-hoc se non c'è un certificato) e, se sono impostate
le variabili `MACOS_CERT_P12`, `MACOS_CERT_PASSWORD`, `MACOS_NOTARY_APPLE_ID`,
`MACOS_NOTARY_PASSWORD` e `MACOS_NOTARY_TEAM_ID`, importa il certificato,
firma con Developer ID e invia a notarizzazione.

### GitHub Actions

`.github/workflows/build.yml` compila tutto su quattro runner
(`ubuntu-22.04`, `windows-latest`, `macos-latest`, `macos-13`) a ogni push e
pull request, e allega i file alla release quando si pusha un tag `v*`:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Gli artefatti della build (senza tag, quindi senza release) restano
scaricabili dalla pagina della Action per 14 giorni. Senza i secret macOS la
DMG esce firmata ad-hoc: funziona, ma al primo avvio serve *tasto destro →
Apri*.

## Note

- Serve Google Chrome (o Chromium/Edge/Brave) installato. Per indicarne uno
  specifico: `VG_CHROME=/percorso/chrome ./download.sh`.
- Durante l'avvio compare una finestra Chrome: è normale, non chiuderla.
- Se Cloudflare insiste, riprova dopo qualche minuto; il profilo persistente
  evita il challenge alle esecuzioni successive.
- I nomi dei file sono quelli degli asset; i duplicati ricevono l'ID tra
  parentesi quadre.
