# -*- mode: python ; coding: utf-8 -*-

import os
import tiktoken
# tiktoken 라이브러리가 설치된 기본 경로를 가져옵니다.
tiktoken_install_path = tiktoken.__path__[0]

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[], # 필요하다면 _tiktoken.cpython-312-darwin.so 와 같은 파일을 직접 추가할 수도 있습니다.
    datas=[
        (tiktoken_install_path, 'tiktoken'), # tiktoken 라이브러리 폴더 전체를 'tiktoken'이라는 이름으로 패키지 내에 복사
        ('Info.plist', '.'), # Info.plist 파일 포함
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'tiktoken', # 라이브러리 이름 자체도 hiddenimports에 유지하는 것이 좋습니다.
        'pathspec',
        'pyperclip',
        'requests',
        'packaging',
        'appdirs',
        'logging',
        'tiktoken_ext.openai_public',
        'tiktoken_ext.pypi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LLM Prompt Helper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, 
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='LLMPromptHelper.entitlements',
    icon='assets/AppIcon.icns'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas, 
    strip=False,
    upx=True, 
    upx_exclude=[],
    name='LLM Prompt Helper',
)
app = BUNDLE(
    coll,
    name='LLM Prompt Helper.app',
    icon='assets/AppIcon.icns',
    bundle_identifier='com.llmPromptHelper.app',
    info_plist={
        'NSPasteboardUsageDescription': 'This app needs access to the clipboard to copy and paste code snippets.',
        'CFBundleDisplayName': 'LLM Prompt Helper',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
) 