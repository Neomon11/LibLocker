#!/bin/bash
# Build script for LibLocker using PyInstaller
# Creates single-file executables for both client and server

echo "================================"
echo "LibLocker Build Script"
echo "================================"
echo ""

# Check if PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller is not installed!"
    echo "Installing PyInstaller..."
    pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "Failed to install PyInstaller"
        exit 1
    fi
fi

echo "Building LibLocker Server..."
pyinstaller server.spec --clean
if [ $? -ne 0 ]; then
    echo "Failed to build server"
    exit 1
fi

echo ""
echo "Building LibLocker Client..."
pyinstaller client.spec --clean
if [ $? -ne 0 ]; then
    echo "Failed to build client"
    exit 1
fi

echo ""
echo "================================"
echo "Build Complete!"
echo "================================"
echo ""
echo "Executables can be found in the 'dist' folder:"
echo "- dist/LibLockerServer (or LibLockerServer.exe on Windows)"
echo "- dist/LibLockerClient (or LibLockerClient.exe on Windows)"
echo ""
echo "Copy these files to target machines and run them."
echo "The client will automatically discover servers in the local network."
echo ""
