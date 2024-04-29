# Create shortcut on the desktop
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path -Path $desktopPath -ChildPath "ViperBoxInterface.lnk"
$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "\logo.ico"
# Create the shortcut
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = Join-Path -Path (Split-Path -Path $PSScriptRoot -Parent) -ChildPath "start_app.bat"
$Shortcut.IconLocation = $iconPath
$Shortcut.Save()
