<#
  Removes PDF Dad. The search index and settings (data\) are kept unless -All is given.
  Usage:  powershell -ExecutionPolicy Bypass -File uninstall.ps1 [-Root <folder>] [-All]
#>
param(
    [string]$Root = "$env:LOCALAPPDATA\PdfDad",
    [switch]$All
)
$AppName = "PDF Dad"
foreach ($dir in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
    Remove-Item (Join-Path $dir "$AppName.lnk") -ErrorAction SilentlyContinue
}
if (Test-Path $Root) {
    Get-ChildItem $Root | Where-Object { $All -or $_.Name -ne "data" } | Remove-Item -Recurse -Force
    if ($All) { Remove-Item $Root -Recurse -Force -ErrorAction SilentlyContinue }
}
Write-Host "UNINSTALL DONE"
