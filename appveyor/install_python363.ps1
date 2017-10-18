# Install Python 3.6.3 over Python 3.6.1
#
# See:
# https://www.appveyor.com/docs/build-environment/#python
# H/T:
# https://github.com/numpy/windows-wheel-builder/blob/master/install_python362.ps1

$py_url = "https://www.python.org/ftp/python"

# First do 32-bit.
$exe_suffix=""
$target_dir="C:\\Python36"
$launcher=0
Write-Host "Installing Python 3.6.3$exe_suffix..." -ForegroundColor Cyan
$exePath = "$env:TEMP\python-3.6.3${exe_suffix}.exe"
$downloadFile = "$py_url/3.6.3/python-3.6.3${exe_suffix}.exe"
Write-Host "Downloading $downloadFile..."
(New-Object Net.WebClient).DownloadFile($downloadFile, $exePath)
Write-Host "Installing..."
cmd /c start /wait $exePath /quiet TargetDir="$target_dir" Shortcuts=0 Include_launcher=$launcher InstallLauncherAllUsers=$launcher
Write-Host "Python 3.6.3 installed to $target_dir"

echo "$(& $target_dir\python.exe --version 2> $null)"

# Then do 64-bit.
$exe_suffix="-amd64"
$target_dir="C:\\Python36-x64"
$launcher=1
Write-Host "Installing Python 3.6.3$exe_suffix..." -ForegroundColor Cyan
$exePath = "$env:TEMP\python-3.6.3${exe_suffix}.exe"
$downloadFile = "$py_url/3.6.3/python-3.6.3${exe_suffix}.exe"
Write-Host "Downloading $downloadFile..."
(New-Object Net.WebClient).DownloadFile($downloadFile, $exePath)
Write-Host "Installing..."
# WAS: cmd /c start /wait $exePath /quiet TargetDir="$target_dir" Shortcuts=0 Include_launcher=$launcher InstallLauncherAllUsers=$launcher
cmd /c start /wait $exePath TargetDir="$target_dir" Shortcuts=0 Include_launcher=$launcher InstallLauncherAllUsers=$launcher
Write-Host "Python 3.6.3 installed to $target_dir"

echo "$(& $target_dir\python.exe --version 2> $null)"
