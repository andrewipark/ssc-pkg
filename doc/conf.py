# Sphinx conf.py

# path setup

import os
import sys
sys.path.insert(0, os.path.abspath('..'))


# project information

project = 'ssc-pkg'
copyright = '2020, andrewipark'
author = 'andrewipark'
# TODO: single sourced version


# general configuration

extensions = [
	'sphinx.ext.autodoc',
	'sphinx.ext.coverage',
	'sphinx.ext.napoleon',
]

templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# html
html_theme = 'alabaster'
html_static_path = ['_static']
