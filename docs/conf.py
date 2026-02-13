"""Sphinx configuration for SeismoAlert documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "SeismoAlert"
copyright = "2026, Utpal Kumar"
author = "Utpal Kumar"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
