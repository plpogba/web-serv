import sys
import os

# 프로젝트 루트 경로 추가 (app 모듈을 찾을 수 있게)
sys.path.insert(0, os.path.abspath('../..'))

project = 'WEB-SERVICE'
copyright = '2026, jinoo'
author = 'jinoo'
release = 'n'

# ✅ 핵심 수정 부분
extensions = [
    'sphinx.ext.autodoc',   # automodule 디렉티브 활성화
    'sphinx.ext.napoleon',  # Google Style docstring 파싱
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'python'

html_theme = 'alabaster'
html_static_path = ['_static']