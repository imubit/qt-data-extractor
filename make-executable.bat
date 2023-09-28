@echo off
pyinstaller --distpath ..\dist\windows --workpath ..\build --hiddenimport win32timezone --hiddenimport data_agent  -n data-extractor -F "src/qt_data_extractor/main.py" --add-data "src\qt_data_extractor\design\*.ui;design" --additional-hooks-dir "src\qt_data_extractor\hooks" --icon=static\logo-256.ico --windowed
