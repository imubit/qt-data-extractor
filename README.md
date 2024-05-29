<!-- These are examples of badges you might want to add to your README:
     please update the URLs accordingly

[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/qt-data-extractor.svg)](https://anaconda.org/conda-forge/qt-data-extractor)
[![Monthly Downloads](https://pepy.tech/badge/qt-data-extractor/month)](https://pepy.tech/project/qt-data-extractor)
[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/qt-data-extractor)
-->

[![ReadTheDocs](https://readthedocs.org/projects/qt-data-extractor/badge/?version=latest)](https://qt-data-extractor.readthedocs.io/en/stable/)
[![PyPI-Server](https://img.shields.io/pypi/v/qt-data-extractor.svg)](https://pypi.org/project/qt-data-extractor/)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](https://pyscaffold.org/)

# Industrial Data Extractor

Industrial Data Extractor is an open-source Windows application to extract process data from industrial systems
and historians. The extractor supports browsing historian tags and extracting periods of data into zipped CSV files.

Supported historians are:

* [Aveva (Osisoft) PI](osisoft-pi)
* [AspenTech InfoPlus.21](aspen-ip21)

## Installation

Please use https://github.com/imubit/qt-data-extractor/releases to download the latest version of the extractor.
You can use Windows setup file to install Data Extractor on Windows workstation or you can use Extractor executable to run the extractor without installation.

### Python Install

Python package distribution is available in addition to Windows installer:

```python
pip install qt-data-extractor
```

Starting the application from Windows Power Shell:

```
PS C:\> qt-data-extractor
```

* If the application is not starting this way, Python Scripts directory is probably not in the PATH. In this case you can run the script from Python installation directory (i.e. `c:\Python\Python39\Scripts\qt-data-extractor.exe`)

## Getting Started

* Configure the target historian using `Server` drop down.
* Using left panel filter editor to browse for tags or import an Excel sheet with a list of tags.
* Select tags you would like to extract on left panel and add then to the right panel with `Add to Selected Tags` button.
* Select a period to be extracted and sample rate (use `Raw Data` option to extract the original sample rate that is stored within the historian).
* Select `Save Directory` in which your archive will be populated.
* Click `Extract` and confirm your selection.
* Wait until extraction is finished.

Read documentation for a specific historian before attempting to extract data.
