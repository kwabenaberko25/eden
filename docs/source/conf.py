import os
import sys
from datetime import datetime

# Path setup
sys.path.insert(0, os.path.abspath('../../'))

# Project information
project = 'Eden Framework'
copyright = f'{datetime.now().year}, Antigravity'
author = 'Antigravity'
release = '1.0.0'

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'myst_parser',
    'sphinxcontrib.mermaid',
]

templates_path = ['_templates']
exclude_patterns = []

# HTML output configuration
html_theme = 'furo'
html_theme_options = {}

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]

# Source suffix
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
