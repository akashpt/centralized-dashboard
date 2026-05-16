#!/bin/bash

echo "============================================"
echo "🚀 Building Armstrong Flask App (Linux)"
echo "============================================"

# Remove old build artifacts
rm -rf build
rm -rf dist
rm -f ArmstrongDashboard.spec

# Run PyInstaller
pyinstaller --onedir \
    --name="ArmstrongDashboard" \
    --icon=static/fabvi_logo.png \
    --hidden-import=flask \
    --hidden-import=jinja2 \
    --hidden-import=werkzeug \
    --hidden-import=pymysql \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --add-data "get_mysql.py:." \
    main.py

echo
echo "✅ Build Completed Successfully!"
