#!/bin/bash
set -euo pipefail

echo "Uninstalling mdi..."

rm -f /usr/local/bin/mdi

if [ -e /usr/local/bin/mdi ]; then
    echo "mdi was not uninstalled successfully"
    exit 1
fi

echo "Uninstall complete"
