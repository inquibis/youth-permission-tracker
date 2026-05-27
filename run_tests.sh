#!/usr/bin/env bash
# Quick test runner script for API unit tests

set -e

echo "=========================================="
echo "Youth Permission Tracker - API Unit Tests"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r test-requirements.txt
fi

echo ""
echo "📋 Running API Unit Tests..."
echo ""

# Run tests with coverage
pytest tests/unit/api/ \
    -v \
    --tb=short \
    --cov=api_base \
    --cov-report=term-missing \
    --color=yes

echo ""
echo "✅ Test run complete!"
echo ""
