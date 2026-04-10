import sys
import os

# docs/source/ 기준으로 프로젝트 루트까지 올라가야 함
sys.path.insert(0, os.path.abspath('../..'))  # ← web-service/ 루트를 가리켜야 함

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

napoleon_google_docstring = True