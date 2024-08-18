# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from quickie import _meta

project = "Quickie Runner"
copyright = "2024, Adrian Martinez Rodriguez"
author = "Adrian Martinez Rodriguez"
release = _meta.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_toolbox.sidebar_links",
    "sphinx_toolbox.github",
]

templates_path = ["_templates"]
exclude_patterns = []


autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

highlight_language = "python3"

github_username = "adrianmrit"
github_repository = "quickie"
