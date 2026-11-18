# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for a single-file, windowed Windows EXE.
# Build with:  pyinstaller --noconfirm --clean OperatieBureaucratie.spec

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets", "assets"),
        ("levels", "levels"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "numpy", "unittest", "pydoc", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OperatieBureaucratie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon="assets/icon.ico",
    version="version_info.txt",
)
