<!-- These are examples of badges you might want to add to your README:
     please update the URLs accordingly

[![ReadTheDocs](https://readthedocs.org/projects/qt-data-extractor/badge/?version=latest)](https://qt-data-extractor.readthedocs.io/en/stable/)
[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/qt-data-extractor.svg)](https://anaconda.org/conda-forge/qt-data-extractor)
[![Monthly Downloads](https://pepy.tech/badge/qt-data-extractor/month)](https://pepy.tech/project/qt-data-extractor)
[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/qt-data-extractor)
-->

[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](https://pyscaffold.org/)

# Industrial Data Extractor

Industrial Data Extractor is an open-source Windows application to extract process data from industrial systems
and historians.

The following systems are currently supported:

* Osisoft PI

It supports browsing and selecting tags on the target system and extract periods of data into zipped CSVs.

## Getting Started

* Configure the target historian using `Server` drop down.
* Using left panel filter editor to browse for tags or import an Excel sheet with a list of tags.
* Select tags you would like to extract on left panel and add then to the right panel with `Add to Selected Tags` button.
* Select a period to be extracted and sample rate (use `Raw Data` option to extract the original sample rate that is stored within the historian).
* Select `Save Directory` in which your archive will be populated.
* Click `Extract` and confirm your selection.
* Wait until extraction is finished.

## Development

### Python Install

```python
pip install qt-data-extractor
```

### Running under CLI

```
PS C:\> qt-data-extractor
```

### Building Windows Executable

```bash
pipx run tox -e winexe
```
