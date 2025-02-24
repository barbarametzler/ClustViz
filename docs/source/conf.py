# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import sys
current_dir = os.path.dirname(__file__)
target_dir = os.path.abspath(os.path.join(current_dir, "../../"))
target_dir_internal = os.path.abspath(os.path.join(current_dir, "../../clustviz/"))  # for chameleon
sys.path.insert(0, target_dir)
sys.path.insert(1, target_dir_internal)

print(target_dir)
# sys.path.insert(0, os.path.abspath('../../clustviz'))


# -- Project information -----------------------------------------------------

project = 'ClustViz'
copyright = '2020, Guglielmo Sanchini'
author = 'Guglielmo Sanchini'

# The full version, including alpha/beta/rc tags
release = '0.0.6'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx_autodoc_typehints',
              'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# to remove full name in methods and packages
add_module_names = False
# to ensure compatibility with ReadTheDocs
master_doc = 'index'

# TODO: make it work, there is a bug apparently right now in sphinx
autodoc_type_aliases = {'CubeInfo': 'denclue.CubeInfo', 'Cubes': 'denclue.Cubes',
                        'CubesCoords': 'denclue.CubesCoords'}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
