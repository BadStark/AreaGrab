@echo off
setlocal
rem AreaGrab installer launcher.
rem Some antivirus/sandbox setups block Inno Setup from creating its temp
rem folder under %TEMP%. This wrapper points TEMP/TMP to a folder next to
rem the installer, then starts the real setup.

set "SETUP=%~dp0AreaGrab_Setup_1.1.0.exe"
if not exist "%SETUP%" (
  echo AreaGrab_Setup_1.1.0.exe not found next to this file.
  pause
  exit /b 1
)

set "TEMP=%~dp0installer-temp"
set "TMP=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%" >nul 2>&1
if not exist "%TEMP%" (
  echo Could not create "%TEMP%".
  echo Extract the portable ZIP instead: AreaGrab_1.1.0_portable.zip
  pause
  exit /b 1
)

start "" "%SETUP%"
