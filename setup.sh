#!/bin/bash
# Setup script for Data Assistant

echo "Setting up Data Assistant..."

# Check if virtual environment exists
if [ ! -d "env" ]; then
    echo "Error: Virtual environment not found. Please create one first:"
    echo "   python3 -m venv env"
    echo "   source env/bin/activate"
    exit 1
fi

# Activate virtual environment
if [ -f "env/bin/activate" ]; then
    source env/bin/activate
else
    echo "Warning: Please activate virtual environment manually:"
    echo "   source env/bin/activate"
    exit 1
fi

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "Initializing knowledge base..."
python -m app.rag.ingest

echo "Running validation tests..."
python tests/test_system.py

echo ""
echo "Setup complete!"
echo ""
echo "To start the application:"
echo "   chainlit run run.py -w"
echo ""