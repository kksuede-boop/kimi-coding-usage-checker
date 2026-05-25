#!/bin/bash
# Setup script for Kimi Coding Usage Checker
# Run this once to install dependencies

pip install -r requirements.txt
playwright install chromium
echo "Setup complete! Run: python check_usage.py"
