# Ensure the script is running with administrative privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}
Write-Host "Starting installer..." -ForegroundColor Yellow
# Check for Anaconda3 and Miniconda in user folder and ProgramData folder
$userFolder = [Environment]::GetFolderPath("UserProfile")
$programDataFolder = [Environment]::GetFolderPath("CommonApplicationData")

Write-Host "Found $($userFolder) and $($programDataFolder)" -ForegroundColor Yellow

$anaconda3Path = Get-ChildItem -Path $userFolder, $programDataFolder -Filter "anaconda3" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
$minicondaPath = Get-ChildItem -Path $userFolder, $programDataFolder -Filter "miniconda" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

# Save the locations in variables
$tmpPath = if ($minicondaPath) { $minicondaPath } else { $null }
$anacondaLocation = if ($anaconda3Path) { $anaconda3Path } else { $tmpPath }

if (-not $anacondaLocation) {
    Write-Host "Anaconda3 or Miniconda not found." -ForegroundColor Yellow
}
else {
    Write-Host "Anaconda3 or Miniconda found at $($anacondaLocation)" -ForegroundColor Green

}

$anacondaSoftware = @{
    "Anaconda" = @{
        "url"       = "https://repo.anaconda.com/archive/Anaconda3-2023.09-0-Windows-x86_64.exe"
        "checkPath" = "$userFolder\anaconda3"
    }
}

# if @anacondaLocation is null, install Anaconda
if (-not $anacondaLocation) {
    $ProgressPreference = 'SilentlyContinue'
    if (Test-Path -Path $anacondaSoftware.Value.checkPath) {
        Write-Host "$($anacondaSoftware.Name) is already installed." -ForegroundColor Green
    }
    else {
        Write-Host "Installing Anaconda. This might take a while, go grab a coffee and check again in 20 to 40 minutes. Don't be fooled, this line will be here for a long time but be patient." -ForegroundColor Yellow
        $installerPath = "$env:TEMP\$($anacondaSoftware.Name).exe"
        Invoke-WebRequest -Uri $anacondaSoftware.Value.url -OutFile $installerPath
        Start-Process -FilePath $installerPath -Wait -ArgumentList "/S /AddToPath=1"
        Remove-Item -Path $installerPath
        Write-Host "$($anacondaSoftware.Name) has been installed." -ForegroundColor Green
    }
}

$anacondaLocation = "$userFolder\anaconda3"

# Define URLs and paths for software installations
$software = @{
    "OpenEphys" = @{
        "url"       = "https://openephysgui.jfrog.io/artifactory/Release-Installer/windows/Install-Open-Ephys-GUI-v0.6.6.exe"
        "checkPath" = "C:\Program Files\Open Ephys"
    }
    "Git"       = @{
        "url"       = "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe"
        "checkPath" = "C:\Program Files\Git"
    }
}
# Install the software
$ProgressPreference = 'SilentlyContinue'
foreach ($s in $software.GetEnumerator()) {
    if (Test-Path -Path $s.Value.checkPath) {
        Write-Host "$($s.Name) is already installed." -ForegroundColor Green
    }
    else {
        Write-Host "Installing $($s.Name)..." -ForegroundColor Yellow
        $installerPath = "$env:TEMP\$($s.Name).exe"
        Invoke-WebRequest -Uri $s.Value.url -OutFile $installerPath
        Start-Process -FilePath $installerPath -Wait
        Remove-Item -Path $installerPath
        Write-Host "$($s.Name) has been installed." -ForegroundColor Green
    }
}

# Update the conda base environment and create a new environment
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$envYamlPath = Join-Path -Path $scriptPath -ChildPath "viperbox.yaml"
Write-Host "Updating base conda and creating a new environment for ViperBox, this, again, might take a while." -ForegroundColor Yellow
# Start-Process -FilePath "$anacondaLocation\Scripts\conda.exe" -ArgumentList "info --envs" -Wait
Start-Process -FilePath "$anacondaLocation\Scripts\conda.exe" -ArgumentList "update -n base conda -y" -Wait
Start-Process -FilePath "$anacondaLocation\Scripts\conda.exe" -ArgumentList "env create -f `"$envYamlPath`" -y" -Wait

# Create a startup file called start_app.bat that always starts in the right location
$mainFolderPath = Split-Path -Parent $scriptPath
$batchFilePath = Join-Path -Path $mainFolderPath -ChildPath "start_app.bat"
$batchContent = "@echo off`ncd /d `"%~dp0`"`ncall conda activate viperbox`nuvicorn main:app --reload < nul`n"
Set-Content -Path $batchFilePath -Value $batchContent

# Create shortcut on the desktop
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path -Path $desktopPath -ChildPath "ViperBoxAPI.lnk"
$iconPath = Join-Path -Path $scriptPath -ChildPath "\logo.ico"
# Create the shortcut
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $batchFilePath
$Shortcut.IconLocation = $iconPath
$Shortcut.Save()

Write-Host "All tasks completed!" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
