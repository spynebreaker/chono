<#
  Removes Chono. The search index and settings (data\) are kept unless -All is given.
  Usage:  powershell -ExecutionPolicy Bypass -File uninstall.ps1 [-Root <folder>] [-All]
#>
param(
    [string]$Root = "$env:LOCALAPPDATA\Chono",
    [switch]$All
)
$AppName = "Chono"
foreach ($dir in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
    Remove-Item (Join-Path $dir "$AppName.lnk") -ErrorAction SilentlyContinue
}
# "Open with" and the right-click entry
Unregister-ScheduledTask -TaskName "Chono actualizacion" -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Classes\Chono.PDF" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Classes\SystemFileAssociations\.pdf\shell\Chono" -Recurse -Force -ErrorAction SilentlyContinue
Remove-ItemProperty "HKCU:\Software\Classes\.pdf\OpenWithProgids" -Name "Chono.PDF" -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Classes\Chono.Office" -Recurse -Force -ErrorAction SilentlyContinue
foreach ($ext in ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp") {
    Remove-ItemProperty "HKCU:\Software\Classes\$ext\OpenWithProgids" -Name "Chono.Office" -ErrorAction SilentlyContinue
}
if (Test-Path $Root) {
    Get-ChildItem $Root | Where-Object { $All -or $_.Name -ne "data" } | Remove-Item -Recurse -Force
    if ($All) { Remove-Item $Root -Recurse -Force -ErrorAction SilentlyContinue }
}
Write-Host "UNINSTALL DONE"
