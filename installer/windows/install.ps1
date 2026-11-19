<#
  Chono installer for Windows. No administrator rights needed.

  Installs everything under %LOCALAPPDATA%\Chono:
    mm\        micromamba (package manager, single exe)
    env\       Python 3.12 + Tk + Tesseract + Ghostscript (conda-forge) + pip packages
    tessdata\  Spanish, old Spanish, English and orientation models
    pdfcraft\  PdfCraft portable build (SHA256 checked)
    kraken\    handwriting engine (Kraken + PyTorch CPU), own environment
    models\    handwriting model (PP-OCRv6 small, SHA256 checked)
    app\       this app
  and adds a desktop and Start menu shortcut.

  Usage:  powershell -ExecutionPolicy Bypass -File install.ps1 [-Root <folder>] [-NoShortcuts] [-NoHandwriting]
#>
param(
    [string]$Root = "$env:LOCALAPPDATA\Chono",
    [switch]$NoShortcuts,
    [switch]$NoHandwriting
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$AppName = "Chono"
$PdfCraftVersion = "0.21.1"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Resolve-Path (Join-Path $Here "..\..")

New-Item -ItemType Directory -Force $Root | Out-Null
$Log = Join-Path $Root "install.log"
function Step($m) { $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; Write-Host $line; Add-Content -Path $Log -Value $line -Encoding utf8 }
function Get($url, $out) { Invoke-WebRequest -UseBasicParsing $url -OutFile $out }

Step "install start, root=$Root"

# 1. micromamba
$mm = Join-Path $Root "mm\micromamba.exe"
if (-not (Test-Path $mm)) {
    New-Item -ItemType Directory -Force (Split-Path $mm) | Out-Null
    Get "https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-win-64" $mm
}
Step "micromamba ok"

# 2. environment
$env:MAMBA_ROOT_PREFIX = Join-Path $Root "mm\root"
$envDir = Join-Path $Root "env"
if (-not (Test-Path (Join-Path $envDir "python.exe"))) {
    & $mm create -y -q -p $envDir -c conda-forge python=3.12 tk tesseract ghostscript | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "micromamba create failed ($LASTEXITCODE)" }
}
$py = Join-Path $envDir "python.exe"
& $py -m pip install -q --disable-pip-version-check -r (Join-Path $Repo "installer\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed ($LASTEXITCODE)" }
Step "environment ok"

# 3. OCR language models
$td = Join-Path $Root "tessdata"
New-Item -ItemType Directory -Force $td | Out-Null
$models = @{
    "spa"     = "https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata"
    "spa_old" = "https://github.com/tesseract-ocr/tessdata_best/raw/main/spa_old.traineddata"
    "eng"     = "https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata"
    "osd"     = "https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata"
}
foreach ($k in $models.Keys) {
    $f = Join-Path $td "$k.traineddata"
    if (-not (Test-Path $f)) { Get $models[$k] $f }
}
# Tesseract also needs its config files (hocr, txt, pdf) next to the models
$condaTd = Get-ChildItem $envDir -Recurse -Directory -Filter configs |
    Where-Object { $_.Parent.Name -eq "tessdata" } | Select-Object -First 1
if (-not $condaTd) { throw "tesseract configs not found in environment" }
Copy-Item (Join-Path $condaTd.Parent.FullName "*") $td -Recurse -Force
Step "tessdata ok"

# 4. PdfCraft portable, checksum verified
$pc = Join-Path $Root "pdfcraft"
if (-not (Get-ChildItem $pc -Recurse -Filter pdfcraft.exe -ErrorAction SilentlyContinue)) {
    $base = "https://github.com/storytold/pdfcraft/releases/download/v$PdfCraftVersion"
    $zip = Join-Path $Root "pdfcraft.zip"
    $sums = Join-Path $Root "SHA256SUMS.txt"
    Get "$base/pdfcraft-$PdfCraftVersion-windows-x64-portable.zip" $zip
    Get "$base/SHA256SUMS.txt" $sums
    $h = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    if (-not (Select-String -Path $sums -Pattern $h -Quiet)) { throw "PdfCraft checksum mismatch" }
    Expand-Archive $zip -DestinationPath $pc -Force
    Remove-Item $zip, $sums
}
Step "pdfcraft ok"

# 4a. Chono's PdfCraft build: the same version with patches/pdfcraft-xfa-chono.patch applied,
# so scripted government forms (Validate buttons, barcodes) work. It replaces the two programs
# of the portable build; the mark file tells Chono they are the patched ones. If it can't be
# downloaded, the plain build stays and Chono offers the other form reader for those forms.
$PatchedTag = "pdfcraft-0.21.1-chono8"
$PatchedSha = "ec5d57736e80b1e3a90efec71056024b9d7faaae4c73c8ef684464bdcd3f2135"
$pcExe = Get-ChildItem $pc -Recurse -Filter pdfcraft.exe | Select-Object -First 1
$mark = Join-Path $pcExe.DirectoryName "CHONO_PATCHED.txt"
if (-not ((Test-Path $mark) -and (Select-String -Path $mark -Pattern $PatchedTag -SimpleMatch -Quiet))) {
    try {
        $pz = Join-Path $Root "pdfcraft-chono.zip"
        Get "https://github.com/spynebreaker/chono/raw/pdfcraft-build/pdfcraft-chono-windows-x64.zip" $pz
        if ((Get-FileHash $pz -Algorithm SHA256).Hash.ToLower() -ne $PatchedSha) { throw "checksum mismatch" }
        $tmp = Join-Path $Root "pdfcraft-chono"
        Expand-Archive $pz -DestinationPath $tmp -Force
        Copy-Item (Join-Path $tmp "*") $pcExe.DirectoryName -Force
        Remove-Item $pz, $tmp -Recurse -Force
        Step "pdfcraft (Chono build $PatchedTag) ok"
    } catch {
        Step "pdfcraft Chono build not installed ($_); the plain build stays"
    }
}

# 4b. handwriting engine (about 1.1 GB, a few minutes)
$kr = Join-Path $Root "kraken"
$krExe = Join-Path $kr "Scripts\kraken.exe"
$model = Join-Path $Root "models\small.safetensors"
$ModelSha = "3108259779f5abfed3908a1c9eafba64d17e4a2a169368c539ecfeff04c018f3"
if (-not $NoHandwriting) {
    if (-not (Test-Path $krExe)) {
        & $py -m venv $kr
        if ($LASTEXITCODE -ne 0) { throw "kraken venv failed" }
        $kpy = Join-Path $kr "Scripts\python.exe"
        $req = Join-Path $Repo "installer\kraken-requirements.txt"
        $torch = Select-String -Path $req -Pattern "^torch" | ForEach-Object { $_.Line }
        & $kpy -m pip install -q --disable-pip-version-check --index-url https://download.pytorch.org/whl/cpu @torch
        if ($LASTEXITCODE -ne 0) { throw "torch install failed ($LASTEXITCODE)" }
        & $kpy -m pip install -q --disable-pip-version-check -r $req --extra-index-url https://download.pytorch.org/whl/cpu
        if ($LASTEXITCODE -ne 0) { throw "kraken install failed ($LASTEXITCODE)" }
    }
    if (-not (Test-Path $model)) {
        New-Item -ItemType Directory -Force (Split-Path $model) | Out-Null
        Get "https://zenodo.org/api/records/21788405/files/small.safetensors/content" $model
    }
    if ((Get-FileHash $model -Algorithm SHA256).Hash.ToLower() -ne $ModelSha) {
        Remove-Item $model; throw "handwriting model checksum mismatch"
    }
    Step "handwriting ok"
}

# 5. the app itself
$app = Join-Path $Root "app"
if (Test-Path $app) { Remove-Item $app -Recurse -Force }
Copy-Item (Join-Path $Repo "app") $app -Recurse
Step "app ok"

# 6. self-test: every tool answers
$env:PATH = "$envDir\Library\bin;$envDir;$env:PATH"
$env:TESSDATA_PREFIX = $td
$langs = (& (Join-Path $envDir "Library\bin\tesseract.exe") --list-langs 2>&1) -join " "
if ($langs -notmatch "spa") { throw "tesseract has no Spanish model" }
& $py -c "import ocrmypdf, pypdfium2, pikepdf, pdf2docx, pyhanko, tkinter, cv2; print('imports ok')"
if ($LASTEXITCODE -ne 0) { throw "python imports failed" }
# real OCR round trip on a generated page
$probe = Join-Path $Root "probe"
New-Item -ItemType Directory -Force $probe | Out-Null
& $py -c "from fpdf import FPDF; import pypdfium2 as p; d=FPDF(); d.add_page(); d.set_font('helvetica', size=24); d.cell(0, 20, 'Prueba de lectura Donoso'); d.output(r'$probe\t.pdf'); p.PdfDocument(r'$probe\t.pdf')[0].render(scale=3).to_pil().save(r'$probe\s.pdf', resolution=216)"
& $py -m ocrmypdf -q -l spa --output-type pdf "$probe\s.pdf" "$probe\o.pdf"
if ($LASTEXITCODE -ne 0) { throw "OCR self-test failed ($LASTEXITCODE)" }
Remove-Item $probe -Recurse -Force
if (-not $NoHandwriting) {
    $env:PYTHONUTF8 = "1"
    $kv = (& $krExe --version 2>&1) -join " "
    if ($kv -notmatch "kraken") { throw "kraken self-test failed: $kv" }
    $langs = "$langs; $kv"
}
Step "self-test ok ($langs)"

# 7. shortcuts
if (-not $NoShortcuts) {
    $ws = New-Object -ComObject WScript.Shell
    $targets = @([Environment]::GetFolderPath("Desktop"), (Join-Path ([Environment]::GetFolderPath("Programs")) ""))
    foreach ($dir in $targets) {
        $s = $ws.CreateShortcut((Join-Path $dir "$AppName.lnk"))
        $s.TargetPath = Join-Path $envDir "pythonw.exe"
        $s.Arguments = "-m chono"
        $s.WorkingDirectory = $app
        $ico = Get-ChildItem $pc -Recurse -Filter pdfcraft.exe | Select-Object -First 1
        if ($ico) { $s.IconLocation = $ico.FullName }
        $s.Save()
    }
    Step "shortcuts ok"
}
Set-Content -Path (Join-Path $Root "VERSION") -Value (Get-Content (Join-Path $Repo "VERSION")) -Encoding utf8
Step "INSTALL DONE"
