<#
  Chono updater, started by Chono itself (app\chono\update.py) after copying this file to the
  install folder. Waits for Chono to close, runs the installer of the newest version over the
  installed one (what is already installed is skipped), and opens Chono again.
  Usage: update.ps1 -Root <install folder> -Version <x.y.z> -WaitPid <Chono's process id>
#>
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [string]$Version = "",
    [int]$WaitPid = 0
)
$ProgressPreference = "SilentlyContinue"
$log = Join-Path $Root "update.log"
function Log($m) { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" -Encoding utf8 }
$tmp = Join-Path $Root "update-tmp"
try {
    Log "update to $Version"
    for ($i = 0; $i -lt 120 -and $WaitPid -gt 0 -and (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue); $i++) { Start-Sleep 1 }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force $tmp | Out-Null
    $zip = Join-Path $tmp "src.zip"
    Invoke-WebRequest -UseBasicParsing "https://github.com/spynebreaker/chono/archive/refs/heads/main.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem $tmp -Directory | Select-Object -First 1
    $installer = Join-Path $src.FullName "installer\windows\install.ps1"
    $a = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $installer, "-Root", $Root, "-NoShortcuts")
    # Keep what is installed: the handwriting engine (about 1 GB) only if it is already there.
    if (-not (Test-Path (Join-Path $Root "kraken\Scripts\kraken.exe"))) { $a += "-NoHandwriting" }
    & powershell.exe @a *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    Log "installer exit $LASTEXITCODE"
} catch {
    Log "update failed: $_"
} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    $pyw = Join-Path $Root "env\pythonw.exe"
    if (Test-Path $pyw) { Start-Process $pyw -ArgumentList "-m", "chono" -WorkingDirectory (Join-Path $Root "app") }
}
