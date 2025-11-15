#!/usr/bin/env bash
# Render build script

# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations/setup if needed
# For now, you'll need to manually run the schema.sql after first deploy
echo "Build completed successfully!"
