#!/bin/bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root" >&2
    exit 1
fi

if [[ ! -f mdi.py ]]; then
    echo "mdi.py not found in the current directory." >&2
    exit 1
fi

install -Dm755 mdi.py /usr/local/bin/mdi

echo "mdi installed successfully."
echo "Run it with: mdi"
