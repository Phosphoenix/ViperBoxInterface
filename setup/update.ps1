$fileList = @("main.py", "gui.py", "api_classes.py", "XML_handler.py", "ViperBox.py", "VB_logger.py", "VB_classes.py")
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainFolderPath = Split-Path -Parent $scriptPath
foreach ($file in $fileList) {
    $fileUrl = "https://raw.githubusercontent.com/sbalk/viperboxinterface/dev/$file"
    $fileDestination = Join-Path -Path $mainFolderPath -ChildPath $file
    Invoke-WebRequest -Uri $fileUrl -OutFile $fileDestination
}
# defaults.py
$fileUrl = "https://raw.githubusercontent.com/sbalk/viperboxinterface/dev/defaults/defaults.py"
$fileDestination = Join-Path -Path $mainFolderPath -ChildPath "defaults/defaults.py"
Invoke-WebRequest -Uri $fileUrl -OutFile $fileDestination

# update.ps1
$fileUrl = "https://raw.githubusercontent.com/sbalk/viperboxinterface/dev/setup/update.ps1"
$fileDestination = Join-Path -Path $mainFolderPath -ChildPath "setup/update.ps1"
Invoke-WebRequest -Uri $fileUrl -OutFile $fileDestination

# viperbox.yaml
$fileUrl = "https://raw.githubusercontent.com/sbalk/viperboxinterface/dev/setup/viperbox.yaml"
$fileDestination = Join-Path -Path $mainFolderPath -ChildPath "setup/viperbox.yaml"
Invoke-WebRequest -Uri $fileUrl -OutFile $fileDestination


$userFolder = [Environment]::GetFolderPath("UserProfile")
$anacondaLocation = "$userFolder\anaconda3"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
# how can you start-process but leave the
Start-Process -FilePath "$anacondaLocation\Scripts\conda.exe" -ArgumentList "env update --name viperbox --file .\setup\viperbox.yaml --prune" -Wait -NoNewWindow


Write-Host "ViperBox updated!" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
