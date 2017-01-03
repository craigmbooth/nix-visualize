import os
import setuptools
import sys

PACKAGE_NAME = "nix_visualize"

__version__ = "0.0.1"

setuptools.setup(
    name=PACKAGE_NAME,
    version=__version__,
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    provides=setuptools.find_packages("src"),
    install_requires=open("requirements.txt").readlines(),
    data_files = [],
    entry_points={"console_scripts": [
        "nix_visualize=nix_visualize.visualize_tree:main",
    ]}
)
