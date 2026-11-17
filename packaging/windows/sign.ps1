<#
.SYNOPSIS
    Firma i binari Windows con Authenticode (signtool).

.DESCRIPTION
    Firma eseguibili e DLL con un certificato Code Signing applicando un
    timestamp RFC 3161: senza timestamp la firma diventa "scaduta" quando
    scade il certificato e Windows torna a mostrare l'avviso SmartScreen.

    Il certificato si può passare in tre modi, in ordine di priorità:
      1. -PfxPath / -Password          file .pfx locale
      2. $env:WINDOWS_CERT_PFX_BASE64  .pfx in base64 (così lo passa la CI)
      3. -Thumbprint                   certificato già nello store di Windows
                                       (per token/HSM hardware)

    Senza certificato lo script esce con 0 se si passa -SkipIfUnsigned, così
    le build locali e le pull request funzionano anche senza segreti, mentre
    una CI che *ha* il segreto fallisce se la firma non riesce.

.PARAMETER Bundle
    Cartella del bundle PyInstaller: firma `vgdl.exe` e
    `VG Resource Download.exe`.

.PARAMETER Path
    File o cartelle da firmare. Le cartelle vengono esplorate in cerca di
    .exe e .dll.

.PARAMETER PfxPath
    Percorso del certificato .pfx.

.PARAMETER Password
    Password del .pfx.

.PARAMETER Thumbprint
    SHA-1 del certificato installato nello store.

.PARAMETER TimestampUrl
    Server di timestamp. Default: $env:WINDOWS_TIMESTAMP_URL, altrimenti
    DigiCert.

.PARAMETER Signtool
    Percorso di signtool.exe se non è nel PATH né nel Windows SDK.

.PARAMETER SkipIfUnsigned
    Se non c'è nessun certificato, esce con 0 invece di fallire.

.EXAMPLE
    powershell -File packaging\windows\sign.ps1 -Bundle dist\VGResourceDownload

.EXAMPLE
    powershell -File packaging\windows\sign.ps1 -Path dist -SkipIfUnsigned
#>
[CmdletBinding()]
param(
    [string]$Bundle,

    [string[]]$Path,

    [string]$PfxPath = $env:WINDOWS_CERT_PFX_PATH,
    [string]$Password = $env:WINDOWS_CERT_PASSWORD,
    [string]$Thumbprint = $env:WINDOWS_CERT_THUMBPRINT,

    [string]$TimestampUrl,
    [string]$Signtool,

    [switch]$SkipIfUnsigned
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Say([string]$Message) { Write-Host "==> $Message" }
function Warn([string]$Message) { Write-Host "avviso: $Message" -ForegroundColor Yellow }
function Fail([string]$Message) {
    Write-Host "ERRORE: $Message" -ForegroundColor Red
    exit 1
}

if (-not $TimestampUrl) {
    if ($env:WINDOWS_TIMESTAMP_URL) {
        $TimestampUrl = $env:WINDOWS_TIMESTAMP_URL
    } else {
        $TimestampUrl = 'http://timestamp.digicert.com'
    }
}

# --- certificato ------------------------------------------------------------
$TempPfx = $null
if (-not $PfxPath -and $env:WINDOWS_CERT_PFX_BASE64) {
    Say 'Decodifico il certificato da WINDOWS_CERT_PFX_BASE64'
    $TempPfx = Join-Path ([System.IO.Path]::GetTempPath()) ("vgdl-" + [guid]::NewGuid().ToString('N') + '.pfx')
    try {
        [IO.File]::WriteAllBytes($TempPfx, [Convert]::FromBase64String($env:WINDOWS_CERT_PFX_BASE64))
    } catch {
        Fail "WINDOWS_CERT_PFX_BASE64 non e base64 valido: $($_.Exception.Message)"
    }
    $PfxPath = $TempPfx
}
if ($PfxPath -and -not (Test-Path $PfxPath)) {
    Fail "certificato non trovato: $PfxPath"
}

if (-not $PfxPath -and -not $Thumbprint) {
    if ($SkipIfUnsigned) {
        Write-Host 'Nessun certificato di firma: binari lasciati non firmati.' -ForegroundColor Yellow
        exit 0
    }
    Fail 'nessun certificato: passa -PfxPath, -Thumbprint o WINDOWS_CERT_PFX_BASE64'
}

# --- signtool ---------------------------------------------------------------
function Find-Signtool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # Windows SDK: si prende la versione più recente che ha x64\signtool.exe.
    $sdkRoot = 'C:\Program Files (x86)\Windows Kits\10\bin'
    if (-not (Test-Path $sdkRoot)) { return $null }

    $best = $null
    $bestVersion = $null
    foreach ($dir in (Get-ChildItem $sdkRoot -Directory -ErrorAction SilentlyContinue)) {
        $parsed = New-Object System.Version '0.0'
        if (-not [System.Version]::TryParse($dir.Name, [ref]$parsed)) { continue }
        $candidate = Join-Path $dir.FullName 'x64\signtool.exe'
        if (-not (Test-Path $candidate)) { continue }
        if (-not $bestVersion -or $parsed -gt $bestVersion) {
            $bestVersion = $parsed
            $best = $candidate
        }
    }
    return $best
}

if (-not $Signtool) { $Signtool = Find-Signtool }
if (-not $Signtool -or -not (Test-Path $Signtool)) {
    Fail 'signtool.exe non trovato: installa il Windows SDK o passa -Signtool'
}

# --- file da firmare --------------------------------------------------------
$Targets = New-Object System.Collections.Generic.List[string]

function Add-Target([string]$Item) {
    if (-not (Test-Path $Item)) { Fail "file non trovato: $Item" }
    $info = Get-Item $Item
    if ($info.PSIsContainer) {
        # Solo i binari di primo livello: dentro _internal\ ci sono decine di
        # DLL di terze parti che non sono nostre e che Windows non controlla
        # quando l'app viene avviata.
        $found = Get-ChildItem -Path $Item -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in @('.exe', '.dll') }
        foreach ($f in $found) {
            if (-not $Targets.Contains($f.FullName)) { $Targets.Add($f.FullName) }
        }
    } elseif (-not $Targets.Contains($info.FullName)) {
        $Targets.Add($info.FullName)
    }
}

if ($Bundle) {
    if (-not (Test-Path $Bundle)) { Fail "bundle non trovato: $Bundle" }
    foreach ($name in @('vgdl.exe', 'VG Resource Download.exe')) {
        $exe = Join-Path $Bundle $name
        if (Test-Path $exe) {
            Add-Target $exe
        } else {
            Warn "$name assente in $Bundle"
        }
    }
}
foreach ($item in $Path) {
    if ($item) { Add-Target $item }
}

if ($Targets.Count -eq 0) {
    if ($SkipIfUnsigned) {
        Write-Host 'Nessun file da firmare.' -ForegroundColor Yellow
        exit 0
    }
    Fail 'nessun file da firmare'
}

Say "signtool:   $Signtool"
Say "timestamp:  $TimestampUrl"
Say "file:       $($Targets.Count)"

# --- firma ------------------------------------------------------------------
$failed = @()
foreach ($file in $Targets) {
    $label = Split-Path $file -Leaf
    $signArgs = @('sign', '/fd', 'sha256', '/td', 'sha256', '/tr', $TimestampUrl)
    if ($PfxPath) {
        $signArgs += @('/f', $PfxPath)
        if ($Password) { $signArgs += @('/p', $Password) }
    } else {
        $signArgs += @('/sha1', $Thumbprint)
    }
    $signArgs += $file

    Say "Firma $label"
    & $Signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        Warn "firma fallita per $label (codice $LASTEXITCODE)"
        $failed += $label
        continue
    }

    & $Signtool verify /pa $file
    if ($LASTEXITCODE -ne 0) {
        Warn "verifica fallita per $label"
        $failed += $label
    }
}

if ($TempPfx -and (Test-Path $TempPfx)) {
    Remove-Item $TempPfx -Force -ErrorAction SilentlyContinue
}

if ($failed.Count -gt 0) {
    Fail ('firma non riuscita per: ' + ($failed -join ', '))
}

Say "Firmati e verificati $($Targets.Count) file"
