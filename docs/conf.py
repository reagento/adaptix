import importlib.util
import sys
from datetime import date

import git

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
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'adaptix'
copyright = f'{date.today().year}, Pavel'
author = 'Pavel'
master_doc = 'index'

# -- General configuration ---------------------------------------------------

# I do not want to mutate sys.path
spec = importlib.util.spec_from_file_location('custom_ext', './custom_ext/__init__.py')
module = importlib.util.module_from_spec(spec)
sys.modules['custom_ext'] = module
spec.loader.exec_module(module)

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_copybutton',
    'sphinx_design',
    'sphinx.ext.extlinks',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.apidoc',
    'sphinx_paramlinks',
    'myst_parser',
    'sphinxext.opengraph',
    'sphinx_better_subsection',
    'sphinx_reredirects',

    # local extensions
    'custom_ext.bench_tools',
    'custom_ext.macros',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    'changelog/*'
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'
html_favicon = 'logo/adaptix-light.svg'
html_theme_options = {
    "sidebar_hide_name": True,
    "light_logo": "adaptix-with-title-light.png",
    "dark_logo": "adaptix-with-title-dark.png",
    "light_css_variables": {
        "font-stack--monospace": 'Hack, SFMono-Regular, Menlo, Consolas, Monaco, "Liberation Mono", "Lucida Console", monospace',
    },
    "dark_css_variables": {
        "font-stack--monospace": 'Hack, SFMono-Regular, Menlo, Consolas, Monaco, "Liberation Mono", "Lucida Console", monospace',
    },
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static', 'logo']
html_js_files = ['gurubase-widget.js']

autodoc_type_aliases = {
    'Loader': 'adaptix.Loader',
    'Dumper': 'adaptix.Dumper',
    'Omittable': 'adaptix.Omittable',
}
autodoc_member_order = 'bysource'

apidoc_module_dir = '../src/adaptix'
apidoc_output_dir = 'reference/api'
apidoc_separate_modules = True
# apidoc_toc_file = False
apidoc_extra_args = ['--maxdepth', '1']

python_maximum_signature_line_length = 90

paramlinks_hyperlink_param = 'name'

add_function_parentheses = False

repo = git.Repo(search_parent_directories=True)
benchmark_data_submodule = next(submodule for submodule in repo.submodules if submodule.name == 'benchmark-data')

extlinks = {
    'adaptix-view-repo': (
        'https://github.com/reagento/adaptix/tree/main/%s',
        '%s',
    ),
    'adaptix-view-repo-commit': (
        f'https://github.com/reagento/adaptix/tree/{repo.head.object.hexsha}/%s',
        '%s',
    ),
    'adaptix-benchmarks-data': (
        f'https://raw.githubusercontent.com/reagento/adaptix-benchmarks-data/{benchmark_data_submodule.hexsha}/%s',
        '%s',
    ),
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

pygments_style = "tango"
pygments_dark_style = "native"

redirects = {
    "tutorial": "loading-and-dumping/tutorial.html",
    "extended_usage": "loading-and-dumping/extended-usage.html",
    "specific_types_behavior": "loading-and-dumping/specific-types-behavior.html",

    "contributing": "reference/contributing.html",
    "examples": "reference/examples.html",

    **{
        f"api_reference/{page}": f"../reference/api/{page}.html"
        for page in [
            'modules',
            'adaptix',
            'adaptix.provider',
            'adaptix.retort',
            'adaptix.load_error',
            'adaptix.struct_trail',
        ]
    },
}
