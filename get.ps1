# Short installer for Chono, easy to type by hand on a remote screen:
#   irm https://raw.githubusercontent.com/spynebreaker/chono/main/get.ps1 | iex
# Downloads the current main branch and runs installer\windows\install.ps1.
# CHONO_ROOT (optional, for tests): install into that folder without shortcuts.
& {
    $ErrorActionPreference = "Stop"
    $t = Join-Path $env:TEMP "chono-get"
    Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory $t | Out-Null
    Write-Host "Bajando Chono..."
    Invoke-WebRequest -UseBasicParsing "https://github.com/spynebreaker/chono/archive/refs/heads/main.zip" -OutFile "$t\chono.zip"
    Expand-Archive "$t\chono.zip" $t -Force
    $extra = @()
    if ($env:CHONO_ROOT) { $extra = @("-Root", $env:CHONO_ROOT, "-NoShortcuts") }
    Write-Host "Instalando Chono (10 a 15 minutos)..."
    $ErrorActionPreference = "Continue"  # the installer's tools write warnings to stderr
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$t\chono-main\installer\windows\install.ps1" @extra
    Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
}
