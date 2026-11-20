<#
  Chono installer for Windows. No administrator rights needed.

  Installs everything under %LOCALAPPDATA%\Chono:
    mm\        micromamba (package manager, single exe)
    env\       Python 3.12 + Tk + Tesseract + Ghostscript (conda-forge) + pip packages
    tessdata\  Spanish, old Spanish, English and orientation models
    pdfcraft\  PdfCraft portable build (SHA256 checked)
    kraken\    handwriting engine (Kraken + PyTorch CPU), own environment
    models\    handwriting model (PP-OCRv6 medium, SHA256 checked)
    app\       this app
  and adds a desktop and Start menu shortcut.

  Usage:  powershell -ExecutionPolicy Bypass -File install.ps1 [-Root <folder>] [-NoShortcuts] [-NoHandwriting] [-NoOffice]
#>
param(
    [string]$Root = "$env:LOCALAPPDATA\Chono",
    [switch]$NoShortcuts,
    [switch]$NoHandwriting,
    [switch]$NoOffice
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
$PatchedTag = "pdfcraft-0.21.1-chono10"
$PatchedSha = "ac7536e1063d8068a6cef70cbcc91042d151bf1201c2f4ef28a12f6e6c127435"
$pcExe = Get-ChildItem $pc -Recurse -Filter pdfcraft.exe | Select-Object -First 1
$mark = Join-Path $pcExe.DirectoryName "CHONO_PATCHED.txt"
if (-not ((Test-Path $mark) -and (Select-String -Path $mark -Pattern $PatchedTag -SimpleMatch -Quiet))) {
    try {
        $pz = Join-Path $Root "pdfcraft-chono.zip"
        Get "https://github.com/spynebreaker/chono/releases/download/$PatchedTag/pdfcraft-chono-windows-x64.zip" $pz
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
# PP-OCRv6 medium: fewer errors than small on cursive, about twice the time per page
$model = Join-Path $Root "models\medium.safetensors"
$ModelSha = "15313b51ace64cbfa81f8f6ef25ad64f04e5a6fb7f7823e67b107527bc081ac9"
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
        Get "https://zenodo.org/api/records/21788410/files/medium.safetensors/content" $model
    }
    if ((Get-FileHash $model -Algorithm SHA256).Hash.ToLower() -ne $ModelSha) {
        Remove-Item $model; throw "handwriting model checksum mismatch"
    }
    Remove-Item (Join-Path $Root "models\small.safetensors") -EA SilentlyContinue  # the earlier model
    # Kraken's line finder as safetensors: the Core ML copy inside Kraken can't load on Windows
    Copy-Item (Join-Path $Repo "installer\models\blla.safetensors") (Join-Path $Root "models\blla.safetensors") -Force
    Step "handwriting ok"
}

# 4c. LibreOffice (about 1 GB): "Hacer PDF de un archivo" and opening Word/Excel files.
# An administrative install only unpacks the MSI into a folder: no administrator rights needed.
# Not fatal: without it, everything else works.
$LoVersion = "26.8.3"
$LoSha = "0e6918c273eabbdbbd800ee0dacbbf130a14c13c2e4cec861b06dd59e015bf94"
$lo = Join-Path $Root "libreoffice"
$loMark = Join-Path $lo "CHONO_VERSION.txt"
if (-not $NoOffice -and -not ((Test-Path $loMark) -and ((Get-Content $loMark -Raw).Trim() -eq $LoVersion))) {
    try {
        $msi = Join-Path $env:TEMP "chono-libreoffice.msi"
        Get "https://download.documentfoundation.org/libreoffice/stable/$LoVersion/win/x86_64/LibreOffice_${LoVersion}_Win_x86-64.msi" $msi
        if ((Get-FileHash $msi -Algorithm SHA256).Hash.ToLower() -ne $LoSha) { throw "checksum mismatch" }
        $unpack = Join-Path $Root "libreoffice.new"
        if (Test-Path $unpack) { Remove-Item $unpack -Recurse -Force }
        $p = Start-Process msiexec.exe -ArgumentList @("/a", "`"$msi`"", "/qn", "TARGETDIR=`"$unpack`"") -Wait -PassThru
        if ($p.ExitCode -ne 0) { throw "msiexec exit $($p.ExitCode)" }
        $soffice = Get-ChildItem $unpack -Recurse -Filter soffice.com | Select-Object -First 1
        if (-not $soffice) { throw "soffice.com not found after unpacking" }
        if (Test-Path $lo) { Remove-Item $lo -Recurse -Force }
        Move-Item (Split-Path (Split-Path $soffice.FullName)) $lo
        Remove-Item $unpack -Recurse -Force -EA SilentlyContinue
        Set-Content -Path $loMark -Value $LoVersion -Encoding ascii
        Step "libreoffice $LoVersion ok"
    } catch {
        Step "libreoffice not installed ($_)"
    } finally {
        Remove-Item $msi -EA SilentlyContinue
    }
}

# 5. the app itself
$app = Join-Path $Root "app"
if (Test-Path $app) { Remove-Item $app -Recurse -Force }
Copy-Item (Join-Path $Repo "app") $app -Recurse
Step "app ok"

# 6. self-test: every tool answers.
# When the updater writes this script's output to a log, Windows PowerShell turns anything a
# program prints on stderr (a Python warning, say) into an error, and "Stop" would end the
# install there. The checks below look at exit codes and output instead.
$ErrorActionPreference = "Continue"
$env:PYTHONWARNINGS = "ignore"
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
$ErrorActionPreference = "Stop"

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

# 8. "Open with" and a right-click entry for PDF files (current user only, no administrator).
# Chono is offered, not made the default: Windows keeps that choice for the user.
$pyw = Join-Path $envDir "pythonw.exe"
$cmd = "`"$pyw`" `"$(Join-Path $app 'abrir.pyw')`" `"%1`""
$ico = Get-ChildItem $pc -Recurse -Filter pdfcraft.exe | Select-Object -First 1
$cls = "HKCU:\Software\Classes"
New-Item -Force "$cls\Chono.PDF\shell\open\command" | Out-Null
Set-ItemProperty "$cls\Chono.PDF" -Name "(default)" -Value "Documento PDF"
Set-ItemProperty "$cls\Chono.PDF\shell\open\command" -Name "(default)" -Value $cmd
# the name Windows shows for it in Open with and in Default apps (else "pythonw")
New-Item -Force "$cls\Chono.PDF\Application" | Out-Null
Set-ItemProperty "$cls\Chono.PDF\Application" -Name "ApplicationName" -Value "Chono"
if ($ico) {
    Set-ItemProperty "$cls\Chono.PDF\Application" -Name "ApplicationIcon" -Value "`"$($ico.FullName)`",0"
    New-Item -Force "$cls\Chono.PDF\DefaultIcon" | Out-Null
    Set-ItemProperty "$cls\Chono.PDF\DefaultIcon" -Name "(default)" -Value "`"$($ico.FullName)`",0"
}
New-Item -Force "$cls\.pdf\OpenWithProgids" | Out-Null
New-ItemProperty -Force "$cls\.pdf\OpenWithProgids" -Name "Chono.PDF" -Value "" -PropertyType String | Out-Null
$verb = "$cls\SystemFileAssociations\.pdf\shell\Chono"
New-Item -Force "$verb\command" | Out-Null
Set-ItemProperty $verb -Name "(default)" -Value "Abrir con Chono"
if ($ico) { Set-ItemProperty $verb -Name "Icon" -Value "`"$($ico.FullName)`",0" }
Set-ItemProperty "$verb\command" -Name "(default)" -Value $cmd
# Word, Excel and other documents: offered in "Open with" through Chono's LibreOffice
$loExe = Join-Path $Root "libreoffice\program\soffice.exe"
if (Test-Path $loExe) {
    New-Item -Force "$cls\Chono.Office\shell\open\command" | Out-Null
    Set-ItemProperty "$cls\Chono.Office" -Name "(default)" -Value "Documento"
    Set-ItemProperty "$cls\Chono.Office\shell\open\command" -Name "(default)" -Value "`"$loExe`" `"%1`""
    New-Item -Force "$cls\Chono.Office\Application" | Out-Null
    Set-ItemProperty "$cls\Chono.Office\Application" -Name "ApplicationName" -Value "LibreOffice"
    Set-ItemProperty "$cls\Chono.Office\Application" -Name "ApplicationIcon" -Value "`"$loExe`",0"
    foreach ($ext in ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp") {
        New-Item -Force "$cls\$ext\OpenWithProgids" | Out-Null
        New-ItemProperty -Force "$cls\$ext\OpenWithProgids" -Name "Chono.Office" -Value "" -PropertyType String | Out-Null
    }
}
Step "open with ok"

# 9. Daily quiet update check (current user, no administrator). PDFs opened from Windows never
# show Chono's window, so its own daily check would not run; this one updates when nothing of
# Chono is open and opens no window. A missed time (computer off) runs at the next chance.
try {
    $pywExe = Join-Path $envDir "pythonw.exe"
    $action = New-ScheduledTaskAction -Execute $pywExe -Argument "`"$(Join-Path $app 'actualizar.pyw')`"" -WorkingDirectory $app
    $trigger = New-ScheduledTaskTrigger -Daily -At "11:17"
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName "Chono actualizacion" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Step "update task ok"
} catch {
    Step "update task not created ($_)"
}
Set-Content -Path (Join-Path $Root "VERSION") -Value (Get-Content (Join-Path $Repo "VERSION")) -Encoding utf8
Step "INSTALL DONE"
