#!/bin/bash
# Run Script - Activate venv and run the CLI

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Run the CLI with provided arguments
python -m src.main "$@"
