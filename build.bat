@echo off
REM Build script for LibLocker using PyInstaller
REM Creates single-file executables for both client and server

echo ================================
echo LibLocker Build Script
echo ================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed!
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Building LibLocker Server...
pyinstaller server.spec --clean
if errorlevel 1 (
    echo Failed to build server
    pause
    exit /b 1
)

echo.
echo Building LibLocker Client...
pyinstaller client.spec --clean
if errorlevel 1 (
    echo Failed to build client
    pause
    exit /b 1
)

echo.
echo ================================
echo Build Complete!
echo ================================
echo.
echo Executables can be found in the 'dist' folder:
echo - dist\LibLockerServer.exe
echo - dist\LibLockerClient.exe
echo.
echo Copy these files to target machines and run them.
echo The client will automatically discover servers in the local network.
echo.
pause
