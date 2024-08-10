#!/usr/bin/env python
"""Setup the package quickie."""

from runpy import run_path

from setuptools import find_packages, setup

_INFO = run_path("src/quickie/_meta.py")
_TEST_REQUIRES = [
    "mock",
    "pytest",
    "pytest-cov",
    "pytest-mock",
]

setup(
    # Metadata
    author=_INFO["__author__"],
    author_email=_INFO["__email__"],
    url=_INFO["__home__"],
    use_scm_version=True,
    zip_safe=False,
    # Package modules and data
    packages=find_packages("src"),
    package_dir={"": "src"},
    # Entries
    entry_points={
        "console_scripts": [
            "qck = quickie.cli:main",
        ],
    },
    # Requires
    python_requires=">=3.12",
    install_requires=[
        "classoptions~=0.2.0",
        "frozendict~=2.4.4",
        "oslex~=0.1.3",
        "python-dotenv~=1.0.1",
        "rich~=13.7.1",
        "argcomplete~=3.5.0",
    ],
    setup_requires=[
        "pytest-runner~=6.0.1",
        "setuptools-scm~=8.1.0",
    ],
    tests_require=_TEST_REQUIRES,
    extras_require={"dev": _TEST_REQUIRES},
    # PyPI Metadata
    keywords=["CLI"],
    platforms=["any"],
    classifiers=[
        # See: https://pypi.org/classifiers/
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
    ],
)
