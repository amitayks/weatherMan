#!/bin/bash
# City Weather Poster - Quick Setup Script

set -e

echo "🌤️ City Weather Poster - Setup Script"
echo "======================================"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION or higher is required (found: $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
fi

# Create output directory
mkdir -p output

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Edit config/cities.yaml to configure your cities"
echo "3. Run a test: python -m src.main --city tokyo --dry-run --force"
echo ""
echo "For GitHub Actions:"
echo "1. Push this repo to GitHub"
echo "2. Add secrets in Settings → Secrets → Actions"
echo "3. Enable Actions in the repo settings"
echo ""
