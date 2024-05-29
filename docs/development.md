# Development Information

## Build Process

### Building Windows Executable

```bash
pipx run tox -e winexe
```

### Building MSI Installer

Install environment

```
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco install -y go-msi


```

Build MSI

```
go-msi make --msi dist\windows-msi\ --version 0.1.1
```
