; ---------------------------------------------------------------------------
; Installer Windows (NSIS) per VG Resource Download
;
; Costruito da packaging/windows/build-installer.ps1, che passa i valori con -D:
;
;   makensis /DROOTDIR=... /DDISTDIR=... /DOUTFILE=... /DVERSION=... ^
;            /DVERSION4=... packaging\windows\installer.nsi
;
; Per il bundle arm64 si aggiunge /DARM64: cambia solo l'etichetta mostrata e
; la vista del registro, dato che i file da impacchettare sono già quelli
; giusti (PyInstaller non fa cross-compilazione).
;
; Installa in %PROGRAMFILES%\VG Resource Download con due eseguibili:
;
;   VG Resource Download.exe   GUI, senza console (menu Start / desktop)
;   vgdl.exe                   console, per CLI e TUI
;
; Nessun plugin esterno: solo NSIS standard (MUI2, FileFunc, LogicLib, x64).
; Il comando `vgdl` nel terminale non passa dal PATH di sistema: creiamo un
; piccolo .cmd in %LOCALAPPDATA%\Microsoft\WindowsApps, che è già nel PATH
; dell'utente, così la disinstallazione è solo un Delete.
; ---------------------------------------------------------------------------

Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; --- valori (sovrascritti con /D) -------------------------------------------
!ifndef VERSION
    !define VERSION "1.0.0"
!endif
!ifndef VERSION4
    !define VERSION4 "1.0.0.0"
!endif
!ifndef DISTDIR
    !define DISTDIR "..\..\dist\VGResourceDownload"
!endif
!ifndef OUTFILE
    !define OUTFILE "..\..\dist\VG_Resource_Download-setup.exe"
!endif
!ifndef ROOTDIR
    !define ROOTDIR "..\.."
!endif

; --- architettura ------------------------------------------------------------
; Il bundle è già compilato per una sola architettura: qui serve solo a
; etichettare l'installer e a scegliere la vista del registro corretta.
!ifdef ARM64
    !define APP_ARCH       "ARM64"
    !define APP_ARCH_LABEL " (ARM64)"
!else
    !define APP_ARCH       "x64"
    !define APP_ARCH_LABEL ""
!endif

!define APP_NAME      "VG Resource Download"
!define APP_EXE       "VG Resource Download.exe"
!define APP_CLI       "vgdl.exe"
!define APP_PUBLISHER "blacksoulgem95"
!define APP_ID        "vg-resource-download"
!define APP_URL       "https://github.com/blacksoulgem95/VG_Resource_Download"
!define APP_REGKEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"

Name "${APP_NAME}"
OutFile "${OUTFILE}"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
BrandingText "${APP_NAME} ${VERSION} · ${APP_ARCH}"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${VERSION4}"
VIAddVersionKey "ProductName"     "${APP_NAME}"
VIAddVersionKey "ProductVersion"  "${VERSION}"
VIAddVersionKey "FileVersion"     "${VERSION}"
VIAddVersionKey "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey "LegalCopyright"  "MIT License"
VIAddVersionKey "FileDescription" "${APP_NAME} Setup${APP_ARCH_LABEL}"
VIAddVersionKey "Comments"        "${APP_URL}"

; --- init --------------------------------------------------------------------
; Senza SetRegView un installer a 32 bit finirebbe in WOW6432Node, creando una
; voce di disinstallazione che il pannello di controllo a 64 bit non vede.
; Serve anche per far combaciare la chiave letta da InstallDirRegKey.
Function .onInit
    SetRegView 64
FunctionEnd

Function un.onInit
    SetRegView 64
FunctionEnd

; --- aspetto -----------------------------------------------------------------
!define MUI_ICON   "${ROOTDIR}\packaging\icons\app.ico"
!define MUI_UNICON "${ROOTDIR}\packaging\icons\app.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "$(RunAppText)"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "$(ReadmeText)"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

; --- lingue ------------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "French"

LangString RunAppText ${LANG_ENGLISH} "Start VG Resource Download"
LangString RunAppText ${LANG_ITALIAN} "Avvia VG Resource Download"
LangString RunAppText ${LANG_FRENCH}  "Lancer VG Resource Download"

LangString ReadmeText ${LANG_ENGLISH} "Open the instructions"
LangString ReadmeText ${LANG_ITALIAN} "Apri le istruzioni"
LangString ReadmeText ${LANG_FRENCH}  "Ouvrir les instructions"

LangString SecCore ${LANG_ENGLISH} "Application (required)"
LangString SecCore ${LANG_ITALIAN} "Applicazione (necessaria)"
LangString SecCore ${LANG_FRENCH}  "Application (requise)"

LangString SecCoreDesc ${LANG_ENGLISH} "The program itself"
LangString SecCoreDesc ${LANG_ITALIAN} "Il programma vero e proprio"
LangString SecCoreDesc ${LANG_FRENCH}  "Le programme lui-même"

LangString SecShortcuts ${LANG_ENGLISH} "Start menu and desktop shortcuts"
LangString SecShortcuts ${LANG_ITALIAN} "Scorciatoie nel menu Start e sul desktop"
LangString SecShortcuts ${LANG_FRENCH}  "Raccourcis menu Démarrer et bureau"

LangString SecShortcutsDesc ${LANG_ENGLISH} "Shortcuts to the program and to the uninstaller"
LangString SecShortcutsDesc ${LANG_ITALIAN} "Scorciatoie al programma e al disinstallatore"
LangString SecShortcutsDesc ${LANG_FRENCH}  "Raccourcis vers le programme et le désinstalleur"

LangString SecCli ${LANG_ENGLISH} "Command line tool (vgdl)"
LangString SecCli ${LANG_ITALIAN} "Strumento da riga di comando (vgdl)"
LangString SecCli ${LANG_FRENCH}  "Outil en ligne de commande (vgdl)"

LangString SecCliDesc ${LANG_ENGLISH} "Makes the vgdl command available in the terminal"
LangString SecCliDesc ${LANG_ITALIAN} "Rende disponibile il comando vgdl nel terminale"
LangString SecCliDesc ${LANG_FRENCH}  "Rend disponible la commande vgdl dans le terminal"

LangString AppTip ${LANG_ENGLISH} "Download the assets of a game from The Models Resource"
LangString AppTip ${LANG_ITALIAN} "Scarica gli asset di un gioco da The Models Resource"
LangString AppTip ${LANG_FRENCH}  "Télécharge les ressources d'un jeu depuis The Models Resource"

LangString CliTip ${LANG_ENGLISH} "Command line / terminal version"
LangString CliTip ${LANG_ITALIAN} "Versione da riga di comando / terminale"
LangString CliTip ${LANG_FRENCH}  "Version ligne de commande / terminal"

LangString AskRemoveData ${LANG_ENGLISH} "Also delete the Chrome profile and downloaded files?"
LangString AskRemoveData ${LANG_ITALIAN} "Vuoi eliminare anche il profilo Chrome e i file scaricati?"
LangString AskRemoveData ${LANG_FRENCH}  "Supprimer aussi le profil Chrome et les fichiers téléchargés ?"

; --- pagine -------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${ROOTDIR}\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; =============================================================================
; Installazione
; =============================================================================
Section "$(SecCore)" SEC_CORE
    SectionIn RO
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Bundle onedir: `_internal/` deve stare accanto agli .exe.
    File /r "${DISTDIR}\*.*"

    ; Istruzioni lette dal pulsante della pagina finale.
    FileOpen $0 "$INSTDIR\README.txt" w
    FileWrite $0 "VG Resource Download ${VERSION}$\r$\n"
    FileWrite $0 "=================================$\r$\n$\r$\n"
    FileWrite $0 "VG Resource Download.exe  apre l'interfaccia grafica.$\r$\n"
    FileWrite $0 "vgdl.exe                  riga di comando e interfaccia a terminale.$\r$\n$\r$\n"
    FileWrite $0 "Esempi (dal prompt dei comandi):$\r$\n"
    FileWrite $0 "  vgdl https://models.spriters-resource.com/playstation_2/kh2/$\r$\n"
    FileWrite $0 "  vgdl --tui$\r$\n"
    FileWrite $0 "  vgdl --help$\r$\n$\r$\n"
    FileWrite $0 "Serve Google Chrome installato: il programma lo usa per superare$\r$\n"
    FileWrite $0 "il controllo Cloudflare del sito.$\r$\n$\r$\n"
    FileWrite $0 "Download predefiniti: %USERPROFILE%\Downloads\VG Resource Download$\r$\n"
    FileWrite $0 "Profilo Chrome: %LOCALAPPDATA%\vg-resource-download\chrome-profile$\r$\n"
    FileClose $0

    ; Registro: "App e funzionalità" + cartella di installazione.
    WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\${APP_NAME}" "Version" "${VERSION}"

    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayVersion"       "${VERSION}"
    WriteRegStr   HKLM "${APP_REGKEY}" "Publisher"            "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${APP_REGKEY}" "URLInfoAbout"         "${APP_URL}"
    WriteRegStr   HKLM "${APP_REGKEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE}"
    WriteRegStr   HKLM "${APP_REGKEY}" "InstallLocation"      "$INSTDIR"
    WriteRegStr   HKLM "${APP_REGKEY}" "UninstallString"      '"$INSTDIR\uninstall.exe"'
    WriteRegStr   HKLM "${APP_REGKEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegDWORD HKLM "${APP_REGKEY}" "NoModify" 1
    WriteRegDWORD HKLM "${APP_REGKEY}" "NoRepair" 1

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${APP_REGKEY}" "EstimatedSize" "$0"

    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "$(SecShortcuts)" SEC_SHORTCUTS
    SetShellVarContext all

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0 SW_SHOWNORMAL "" "$(AppTip)"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} (Terminale).lnk" \
        "$INSTDIR\${APP_CLI}" "" "$INSTDIR\${APP_CLI}" 0 SW_SHOWNORMAL "" "$(CliTip)"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Disinstalla ${APP_NAME}.lnk" \
        "$INSTDIR\uninstall.exe"

    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0 SW_SHOWNORMAL "" "$(AppTip)"
SectionEnd

Section "$(SecCli)" SEC_CLI
    ; %LOCALAPPDATA%\Microsoft\WindowsApps è già nel PATH dell'utente su
    ; Windows 10/11: mettendo qui uno stub .cmd il comando `vgdl` funziona
    ; senza toccare il PATH di sistema (e si disinstalla con un Delete).
    SetShellVarContext current
    CreateDirectory "$LOCALAPPDATA\Microsoft\WindowsApps"

    FileOpen $0 "$LOCALAPPDATA\Microsoft\WindowsApps\vgdl.cmd" w
    FileWrite $0 '@echo off$\r$\n'
    FileWrite $0 '"$INSTDIR\${APP_CLI}" %*$\r$\n'
    FileClose $0
SectionEnd

; Descrizioni dei componenti (selettore)
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CORE}      "$(SecCoreDesc)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_SHORTCUTS} "$(SecShortcutsDesc)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CLI}       "$(SecCliDesc)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; =============================================================================
; Disinstallazione
; =============================================================================
Section "Uninstall"
    SetShellVarContext all

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME} (Terminale).lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Disinstalla ${APP_NAME}.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"

    SetShellVarContext current
    Delete "$LOCALAPPDATA\Microsoft\WindowsApps\vgdl.cmd"

    ; Il bundle vero e proprio.
    RMDir /r "$INSTDIR\_internal"
    Delete "$INSTDIR\*.exe"
    Delete "$INSTDIR\*.txt"
    Delete "$INSTDIR\*.dll"
    Delete "$INSTDIR\*.pyd"
    Delete "$INSTDIR\*.zip"
    RMDir  "$INSTDIR"   ; non ricorsivo: se resta qualcosa, non lo cancella

    DeleteRegKey HKLM "${APP_REGKEY}"
    DeleteRegKey HKLM "Software\${APP_NAME}"

    ; Dati personali: chiesti, mai cancellati di nascosto.
    IfFileExists "$LOCALAPPDATA\${APP_ID}\*.*" 0 vgdl_uninstall_done
        MessageBox MB_YESNO|MB_ICONQUESTION "$(AskRemoveData)" /SD IDNO IDNO vgdl_uninstall_done
        RMDir /r "$LOCALAPPDATA\${APP_ID}"
    vgdl_uninstall_done:
SectionEnd
