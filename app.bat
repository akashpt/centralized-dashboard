cho off
REM Kill previous running EXE if exists
taskkill /f /im armstrong_dashboard.exe 2>nul

REM Clean previous builds
rd /s /q build
rd /s /q dist
del armstrong_dashboard.spec

REM Run PyInstaller
pyinstaller --onefile --console ^
--icon=static\fabvi_logo.ico ^
--add-data "templates;templates" ^
--add-data "static;static" ^
--name armstrong_dashboard ^
--hidden-import mysql.connector.plugins.mysql_native_password ^
main.py

echo Build completed! Check the dist folder.
pause
