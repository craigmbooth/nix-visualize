import os
import setuptools
import sys

PACKAGE_NAME = "nix_visualize"

setuptools.setup(
    name=PACKAGE_NAME,
    version="1.0",
    packages=["nix_visualize"],
    install_requires=open("requirements.txt").readlines(),
    data_files = [],
    entry_points={"console_scripts": [
        "nix-visualize=nix_visualize.visualize_tree:main"
    ]}
)
