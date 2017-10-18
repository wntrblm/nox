# Install Python 3.5.4 over Python 3.5.3
#
# See:
# https://www.appveyor.com/docs/build-environment/#python
# H/T:
# https://github.com/numpy/windows-wheel-builder/blob/master/install_python362.ps1

$py_url = "https://www.python.org/ftp/python"

# First do 32-bit.
$exe_suffix=""
$target_dir="C:\\Python35"
Write-Host "Installing Python 3.5.4$exe_suffix..." -ForegroundColor Cyan
$exePath = "$env:TEMP\python-3.5.4${exe_suffix}.exe"
$downloadFile = "$py_url/3.5.4/python-3.5.4${exe_suffix}.exe"
Write-Host "Downloading $downloadFile..."
(New-Object Net.WebClient).DownloadFile($downloadFile, $exePath)
Write-Host "Installing..."
cmd /c start /wait $exePath /passive InstallAllUsers=1 TargetDir="$target_dir" Shortcuts=0 Include_launcher=0 InstallLauncherAllUsers=0
Write-Host "Python 3.5.4 installed to $target_dir"

echo "$(& $target_dir\python.exe --version 2> $null)"

# Then do 64-bit.
$exe_suffix="-amd64"
$target_dir="C:\\Python35-x64"
Write-Host "Installing Python 3.5.4$exe_suffix..." -ForegroundColor Cyan
$exePath = "$env:TEMP\python-3.5.4${exe_suffix}.exe"
$downloadFile = "$py_url/3.5.4/python-3.5.4${exe_suffix}.exe"
Write-Host "Downloading $downloadFile..."
(New-Object Net.WebClient).DownloadFile($downloadFile, $exePath)
Write-Host "Installing..."
cmd /c start /wait $exePath /passive InstallAllUsers=1 TargetDir="$target_dir" Shortcuts=0 Include_launcher=0 InstallLauncherAllUsers=0
Write-Host "Python 3.5.4 installed to $target_dir"

echo "$(& $target_dir\python.exe --version 2> $null)"
