#!/usr/bin/env python
"""Setup the package task-mom."""

from runpy import run_path

from setuptools import find_packages, setup

_INFO = run_path("src/task_mom/_meta.py")
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
            "mom = task_mom.cli:main",
        ],
    },
    # Requires
    python_requires=">=3.12",
    install_requires=[],
    setup_requires=[
        "pytest-runner",
        "setuptools-scm",
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
