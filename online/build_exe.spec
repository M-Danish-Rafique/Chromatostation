# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# ---------------------------------------------------------------------
# Bundle essential UCRT DLLs for Windows 7 / 8 compatibility
# ---------------------------------------------------------------------
ucrt_dlls = []
if sys.platform == 'win32':
    system32 = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
    
    # Essential DLLs for older Windows versions
    essential_dlls = [
        'api-ms-win-core-path-l1-1-0.dll',
        'api-ms-win-core-file-l1-1-0.dll',
        'api-ms-win-core-synch-l1-1-0.dll',
        'api-ms-win-core-processthreads-l1-1-0.dll',
        'api-ms-win-crt-runtime-l1-1-0.dll',
        'api-ms-win-crt-stdio-l1-1-0.dll',
        'api-ms-win-crt-heap-l1-1-0.dll',
        'api-ms-win-crt-locale-l1-1-0.dll',
        'api-ms-win-crt-math-l1-1-0.dll',
        'api-ms-win-crt-string-l1-1-0.dll',
        'api-ms-win-crt-time-l1-1-0.dll',
        'api-ms-win-crt-filesystem-l1-1-0.dll',
        'api-ms-win-crt-convert-l1-1-0.dll',
        'api-ms-win-crt-environment-l1-1-0.dll',
        'ucrtbase.dll',
        'vcruntime140.dll',
        'msvcp140.dll',
    ]
    
    for dll in essential_dlls:
        dll_path = os.path.join(system32, dll)
        if os.path.exists(dll_path):
            ucrt_dlls.append((dll_path, '.'))
        else:
            print(f"WARNING: {dll} not found in System32")

# ---------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=ucrt_dlls,
    datas=[
        ('Resources', 'Resources'),
    ],
    hiddenimports=[
        # ---------------- Tkinter and extensions ----------------
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.font',
        'tkinter.scrolledtext',
        'tkcalendar',
        '_tkinter',
        
        # ---------------- PIL/Pillow ----------------
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.ImageFilter',
        'PIL.ImageResampling',
        'PIL._imaging',
        
        # ---------------- NumPy and Pandas ----------------
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.lib',
        'numpy.lib.format',
        'numpy.random',
        'numpy.random.mtrand',
        'numpy.random.bit_generator',
        'numpy.random._common',
        'numpy.random._generator',
        'pandas',
        'pandas.plotting',
        'pandas.io',
        'pandas.io.formats',
        'pandas.io.formats.style',
        'pandas._libs',
        'pandas._libs.tslibs',
        
        # ---------------- Matplotlib ----------------
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_agg',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.figure',
        'matplotlib.font_manager',
        'matplotlib.dates',
        'matplotlib.ticker',
        
        # ---------------- ReportLab ----------------
        'reportlab',
        'reportlab.platypus',
        'reportlab.pdfgen',
        'reportlab.pdfgen.canvas',
        'reportlab.pdfbase',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.pdfbase.ttfonts',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.utils',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        
        # ---------------- Networking / SSL ----------------
        'socket',
        '_socket',
        'ssl',
        '_ssl',
        'select',
        
        # ---------------- Standard Library (CRITICAL for Win7) ----------------
        'secrets',  # CRITICAL: Required by numpy.random
        'hmac',
        'hashlib',
        '_hashlib',
        'binascii',
        'base64',
        'struct',
        'array',
        'collections',
        'collections.abc',
        'functools',
        'itertools',
        'operator',
        'copy',
        'weakref',
        'email',
        'email.mime',
        'email.mime.base',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.image',
        'http',
        'http.client',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'urllib.error',
        'html',
        'html.parser',
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'json',
        'json.decoder',
        'json.encoder',
        'datetime',
        'time',
        'calendar',
        'tempfile',
        'shutil',
        'io',
        'os',
        'os.path',
        'pathlib',
        'glob',
        're',
        'string',
        'math',
        'decimal',
        'fractions',
        'random',
        'ctypes',
        'ctypes.wintypes',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # -------------------------------------------------
        # CRITICAL: Prevent Win7 crash (multiprocessing issues)
        # -------------------------------------------------
        'multiprocessing',
        'multiprocessing.pool',
        'multiprocessing.managers',
        'multiprocessing.reduction',
        'multiprocessing.context',
        'multiprocessing.shared_memory',
        'multiprocessing.spawn',
        'multiprocessing.popen_spawn_win32',
        
        # ---------------- Test / Dev tools ----------------
        'test',
        'tests',
        'unittest',
        'unittest.mock',
        'pytest',
        'nose',
        
        # ---------------- Documentation ----------------
        'pydoc',
        'pydoc_data',
        'doctest',
        
        # ---------------- Packaging tools ----------------
        'setuptools',
        'distutils',
        'pip',
        'wheel',
        
        # ---------------- Jupyter/IPython ----------------
        'IPython',
        'jupyter',
        'notebook',
        
        # ---------------- Heavy unused libs ----------------
        'scipy',  # Only if you don't use it
        
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------
# PYZ
# ---------------------------------------------------------------------
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ---------------------------------------------------------------------
# EXE
# ---------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='N2000 online chromatostation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True temporarily for debugging if needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Resources/Icon.ico',
)

# ---------------------------------------------------------------------
# COLLECT
# ---------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='N2000 online chromatostation',
)