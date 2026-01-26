#!/bin/bash
# Projektor Quickstart Script
# Szybka inicjalizacja projektora w dowolnym projekcie

set -e

PROJECT_PATH="${1:-.}"
PROJECT_NAME=$(basename "$PROJECT_PATH")

echo "🎬 Projektor Quickstart"
echo "========================"
echo "Project: $PROJECT_NAME"
echo "Path: $PROJECT_PATH"
echo ""

# Check if projektor is available
if ! python3 -c "import projektor" 2>/dev/null; then
    echo "⚠️  Projektor not found. Installing from local source..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    export PYTHONPATH="$SCRIPT_DIR/../src:$PYTHONPATH"
fi

cd "$PROJECT_PATH"

# Step 1: Initialize projektor
echo "📁 Step 1: Initializing projektor..."
python3 -m projektor.cli init "$PROJECT_NAME" 2>/dev/null || echo "   (Already initialized)"

# Step 2: Enable integration
echo "🔧 Step 2: Enabling integration..."
python3 -m projektor.cli integrate init --global-handler

# Step 3: Show status
echo ""
echo "📊 Step 3: Current status:"
python3 -m projektor.cli status

# Step 4: Create first ticket if none exists
TICKET_COUNT=$(ls .projektor/tickets/*.json 2>/dev/null | wc -l || echo "0")
if [ "$TICKET_COUNT" -eq "0" ]; then
    echo ""
    echo "🎫 Step 4: Creating first ticket..."
    python3 -m projektor.cli ticket create "Setup projektor integration" \
        --type task --priority medium \
        --description "Configure projektor for automatic error tracking"
fi

echo ""
echo "✅ Projektor is ready!"
echo ""
echo "📋 Available commands:"
echo "   projektor status          # Show project status"
echo "   projektor live            # Live monitoring (run in separate terminal)"
echo "   projektor ticket list     # List all tickets"
echo "   projektor work on TICKET  # Work on a ticket with LLM"
echo "   projektor errors          # Show recent errors"
echo "   projektor watch           # Watch files for syntax errors"
echo ""
echo "💡 Tip: Run 'projektor live' in one terminal while working in another!"
