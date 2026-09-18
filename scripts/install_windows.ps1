<#
.SYNOPSIS
    Chess Desktop — Windows Desktop & Start Menu Installer
.DESCRIPTION
    Creates shortcuts for Chess Desktop on Windows:
    - Desktop Shortcut: $HOME\Desktop\Chess Desktop.lnk
    - Start Menu Shortcut: $env:APPDATA\Microsoft\Windows\Start Menu\Programs\Chess Desktop.lnk
.PARAMETER Uninstall
    Remove the installed shortcuts.
#>

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$StartMenuPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

$DesktopShortcut = Join-Path $DesktopPath "Chess Desktop.lnk"
$StartMenuShortcut = Join-Path $StartMenuPath "Chess Desktop.lnk"
$IconPath = Join-Path $ProjectRoot "assets\icons\chess-desktop.svg"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$FallbackPython = "pythonw.exe"

if ($Uninstall) {
    Write-Host "Uninstalling Chess Desktop shortcuts..." -ForegroundColor Yellow
    if (Test-Path $DesktopShortcut) { Remove-Item $DesktopShortcut -Force }
    if (Test-Path $StartMenuShortcut) { Remove-Item $StartMenuShortcut -Force }
    Write-Host "Chess Desktop shortcuts removed successfully." -ForegroundColor Green
    Exit 0
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Installing Chess Desktop for Windows" -ForegroundColor Cyan
Write-Host "  Project Root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Determine Python target executable
$TargetExe = ""
$TargetArgs = "-m chess_desktop.main"

if (Test-Path $VenvPython) {
    $TargetExe = $VenvPython
} else {
    $TargetExe = (Get-Command "pythonw.exe" -ErrorAction SilentlyContinue).Source
    if (-not $TargetExe) {
        $TargetExe = (Get-Command "python.exe" -ErrorAction SilentlyContinue).Source
    }
}

if (-not $TargetExe) {
    Write-Error "Python executable not found. Please install Python 3.11+ and run 'uv sync' or 'pip install -e .'."
}

# Create WScript Shell COM object for shortcut creation
$WshShell = New-Object -ComObject WScript.Shell

function Create-Shortcut([string]$ShortcutPath) {
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.Arguments = $TargetArgs
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "Polished offline-first desktop chess with Stockfish AI"
    $Shortcut.Save()
    Write-Host "✔ Created shortcut: $ShortcutPath" -ForegroundColor Green
}

Create-Shortcut -ShortcutPath $DesktopShortcut
Create-Shortcut -ShortcutPath $StartMenuShortcut

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "✔ Chess Desktop is now installed on Windows!" -ForegroundColor Green
Write-Host ""
Write-Host "You can launch it by:" -ForegroundColor White
Write-Host "  1. Clicking 'Chess Desktop' on your Desktop" -ForegroundColor White
Write-Host "  2. Searching 'Chess Desktop' in the Windows Start Menu" -ForegroundColor White
Write-Host ""
Write-Host "To uninstall anytime, run:" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1 -Uninstall" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Cyan
