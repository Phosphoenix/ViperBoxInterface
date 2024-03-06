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

Write-Host "ViperBox updated!" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
