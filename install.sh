#!/bin/bash
# SDModels Backend - Quick Installation Script

echo "=========================================="
echo "  SDModels Backend - Quick Install"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "   Please install Python 3.8 or higher"
    exit 1
fi

# Run the Python installation script
python3 install_dependencies.py

exit $?
