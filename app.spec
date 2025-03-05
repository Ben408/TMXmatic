# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('tmx/Lib/site-packages/PythonTmx', 'PythonTmx'),
    ],
    hiddenimports=[
        'flask',
        'flask.templating',
        'werkzeug',
        'werkzeug.middleware',
        'werkzeug.middleware.proxy_fix',
        'jinja2',
        'jinja2.ext',
        'collections.abc',
        'typing',
        'PythonTmx',
        'datetime',
        'openpyxl',
        'python-dateutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TMX_Processing_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='Icon/favicon.ico'
)
