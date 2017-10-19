:: Build the `py.exe` launcher from source.

@ECHO OFF

call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat"
"C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\cl.exe" .\appveyor\launcher.c advapi32.lib version.lib Shell32.lib /Fepy.exe
