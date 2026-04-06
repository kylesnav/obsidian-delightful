#!/bin/bash
# Build + deploy to Obsidian vault + reload theme
cd "$(dirname "$0")/.."
node build.js
VAULT_THEME="/Users/kylesnav/Library/Mobile Documents/iCloud~md~obsidian/Documents/Base/.obsidian/themes/Delightful/theme.css"
cp theme.css "$VAULT_THEME"
echo "Deployed to vault"
python3 scripts/cdp.py reload 2>&1 || echo "Could not reload (Obsidian not running with CDP?)"
