<#
.SYNOPSIS
    Crea l'installer Windows (NSIS) partendo dal bundle PyInstaller.

.DESCRIPTION
    Usa dist\VGResourceDownload\ già costruito con

        pyinstaller --noconfirm --clean packaging\vgdl.spec

    e produce dist\VG_Resource_Download-<versione>-x64-setup.exe.

.PARAMETER Version
    Versione da mettere nei metadati (default: letta da vg_version.py).

.PARAMETER Makensis
    Percorso di makensis.exe, se non è nel PATH.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\windows\build-installer.ps1
#>
[CmdletBinding()]
param(
    [string]$Version,
    [string]$Makensis
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
    Write-Host "ERRORE: $Message" -ForegroundColor Red
    exit 1
}

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Dist = Join-Path $Root 'dist\VGResourceDownload'

if (-not (Test-Path $Dist)) {
    Fail "bundle non trovato: $Dist (esegui prima PyInstaller)"
}
foreach ($exe in @('vgdl.exe', 'VG Resource Download.exe')) {
    if (-not (Test-Path (Join-Path $Dist $exe))) {
        Fail "eseguibile mancante: $exe in $Dist"
    }
}

# Versione: dal sorgente, così non ci sono due verità.
if (-not $Version) {
    $Version = (& python -c "import vg_version; print(vg_version.__version__)").Trim()
}
if (-not $Version) { Fail 'versione non determinata' }

# NSIS vuole X.X.X.X
$parts = @($Version.Split('.'))
while ($parts.Count -lt 4) { $parts += '0' }
$Version4 = ($parts[0..3] -join '.')

# makensis: parametro, PATH, oppure i percorsi classici dell'installer NSIS.
if (-not $Makensis) {
    $candidates = @(
        (Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        'C:\Program Files (x86)\NSIS\makensis.exe',
        'C:\Program Files\NSIS\makensis.exe'
    ) | Where-Object { $_ -and (Test-Path $_) }
    $Makensis = $candidates | Select-Object -First 1
}
if (-not $Makensis) {
    Fail "makensis.exe non trovato. Installa NSIS (choco install nsis) o passa -Makensis."
}

$OutFile = Join-Path $Root "dist\VG_Resource_Download-$Version-x64-setup.exe"
$Arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
if ($Arch -eq 'arm64') {
    $OutFile = Join-Path $Root "dist\VG_Resource_Download-$Version-arm64-setup.exe"
}

Write-Host "==> NSIS: $Makensis"
Write-Host "==> Sorgente: $Dist"
Write-Host "==> Versione: $Version ($Version4)"
Write-Host "==> Uscita:   $OutFile"

if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

& $Makensis `
    "/DROOTDIR=$Root" `
    "/DDISTDIR=$Dist" `
    "/DOUTFILE=$OutFile" `
    "/DVERSION=$Version" `
    "/DVERSION4=$Version4" `
    (Join-Path $PSScriptRoot 'installer.nsi')

if ($LASTEXITCODE -ne 0) { Fail "makensis è uscito con codice $LASTEXITCODE" }
if (-not (Test-Path $OutFile)) { Fail "installer non prodotto: $OutFile" }

$size = [math]::Round((Get-Item $OutFile).Length / 1MB, 1)
Write-Host ""
Write-Host "Fatto: $OutFile  ($size MB)" -ForegroundColor Green
