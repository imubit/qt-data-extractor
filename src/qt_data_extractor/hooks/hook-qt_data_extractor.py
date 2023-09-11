# https://stackoverflow.com/questions/60851713/pyinstaller-pymeasure-notimplementederror

from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("qt-data-extractor")
