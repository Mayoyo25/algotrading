#!/bin/bash
find . -maxdepth 4 \( -name ".git" -o -name ".venv" -o -name "__pycache__" -o -name ".mypy_cache" -o -name ".pytest_cache" -o -name "*.egg-info" -o -name "build" -o -name "dist" \) -prune -o -not -name "." -print | sed "s/[^/]*\//|  /g" > structure.txt
echo "Project structure saved to structure.txt"

