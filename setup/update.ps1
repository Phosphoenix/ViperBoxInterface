$fileList = @("api_classes.py", "gui.py", "main.py", "mappings.py", "NeuraviperPy.py", "VB_classes.py", "VB_logger.py", "ViperBox.py", "XML_handler.py")
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainFolderPath = Split-Path -Parent $scriptPath -ChildPath "viperboxinterface"
foreach ($file in $fileList) {
    $fileUrl = "https://raw.githubusercontent.com/sbalk/viperboxinterface/main/$file"
    $fileDestination = Join-Path -Path $mainFolderPath -ChildPath $file
    Invoke-WebRequest -Uri $fileUrl -OutFile $fileDestination
}

Write-Host "ViperBox updated!" -ForegroundColor Green

Read-Host -Prompt "Press Enter to exit"
