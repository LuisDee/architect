#!/bin/bash
# Run the full contract test suite
# Usage: ./run_tests.sh [--project /path/to/conductor]
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# Regenerate fixtures (idempotent)
python3 "$DIR/generate_fixtures.py"

if [ "$1" = "--project" ] && [ -n "$2" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  Running against PROJECT: $2"
    echo "═══════════════════════════════════════════════════"
    python3 "$DIR/test_contracts.py" --project "$2"
else
    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "  Running against FIXTURES"
    echo "═══════════════════════════════════════════════════"
    python3 "$DIR/test_contracts.py" --fixtures "$DIR/fixtures"
fi
