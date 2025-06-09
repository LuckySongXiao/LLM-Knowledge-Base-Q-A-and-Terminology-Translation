# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 隐藏导入
hidden_imports = ['numpy', 'scipy', 'sklearn', 'torch', 'torchaudio', 'torchvision', 'transformers', 'accelerate', 'sentence_transformers', 'PySide6', 'jieba', 'modelscope', 'PIL', 'json', 'yaml', 'pyyaml', 'cv2', 'pandas']

# 基础分析
a = Analysis(
    ['AI_assistant.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加数据文件
a.datas += [('config.json', r'config.json', 'DATA')]
a.datas += [('README.md', r'README.md', 'DATA')]
a.datas += [('CHANGELOG.md', r'CHANGELOG.md', 'DATA')]
a.datas += [('data', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\data', 'DATA')]
a.datas += [('data\knowledge', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\data\knowledge', 'DATA')]
a.datas += [('data\terms', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\data\terms', 'DATA')]
a.datas += [('data\vectors', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\data\vectors', 'DATA')]
a.datas += [('data\term_vectors', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\data\term_vectors', 'DATA')]
a.datas += [('check_cuda.py', r'check_cuda.py', 'DATA')]
a.datas += [('create_data_dirs.py', r'create_data_dirs.py', 'DATA')]
a.datas += [('simple_embedding.py', r'simple_embedding.py', 'DATA')]
a.datas += [('app_info.json', r'C:\Users\ADMINI~1\AppData\Local\Temp\ai_assistant_bundle_bsd4e4vi\app_info.json', 'DATA')]

# 添加核心模块目录
if os.path.exists('core'):
    a.datas += collect_data_files('core')
    
# 添加UI模块目录
if os.path.exists('ui'):
    a.datas += collect_data_files('ui')
    
# 添加utils目录
if os.path.exists('utils'):
    a.datas += collect_data_files('utils')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='松瓷机电AI助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
