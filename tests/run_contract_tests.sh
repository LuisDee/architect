#!/bin/bash
# Run the full contract test suite.
#
# Usage:
#   ./tests/run_contract_tests.sh                          # fixtures only
#   ./tests/run_contract_tests.sh --sample-project         # sample project
#   ./tests/run_contract_tests.sh --project /path/to/conductor
#   ./tests/run_contract_tests.sh --all                    # both
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
cd "$ROOT"

# Regenerate fixtures (idempotent)
python3 "$DIR/generate_fixtures.py"

if [ "$1" = "--project" ] && [ -n "$2" ]; then
    echo ""
    echo "======================================================="
    echo "  Running against PROJECT: $2"
    echo "======================================================="
    python3 "$DIR/test_contracts.py" --project "$2"

elif [ "$1" = "--sample-project" ]; then
    echo ""
    echo "======================================================="
    echo "  Running against SAMPLE PROJECT"
    echo "======================================================="
    python3 "$DIR/test_contracts.py" --sample-project

elif [ "$1" = "--all" ]; then
    echo ""
    echo "======================================================="
    echo "  Running against FIXTURES"
    echo "======================================================="
    python3 "$DIR/test_contracts.py" --fixtures "$DIR/fixtures"
    echo ""
    echo "======================================================="
    echo "  Running against SAMPLE PROJECT"
    echo "======================================================="
    python3 "$DIR/test_contracts.py" --sample-project

else
    echo ""
    echo "======================================================="
    echo "  Running against FIXTURES"
    echo "======================================================="
    python3 "$DIR/test_contracts.py" --fixtures "$DIR/fixtures"
fi
