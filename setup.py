import os
import setuptools
import sys

PACKAGE_NAME = "nix_visualize"
VERSION = "1.0.5"
setuptools.setup(
    name=PACKAGE_NAME,
    version=VERSION,
    packages=[PACKAGE_NAME],
    description="CLI to automate generation of pretty Nix dependency trees",
    author="Craig Booth",
    author_email="craigmbooth@gmail.com",
    url="https://github.com/craigmbooth/nix-dependency-visualizer",
    download_url = "https://github.com/craigmbooth/nix-dependency-visualizer/tarball/"+VERSION,
    keywords=["nix", "matplotlib"],
    classifiers=[],
    install_requires=[
        "matplotlib>=1.5",
        "networkx>=1.11",
        "pygraphviz>=1.3",
        "pandas>=1.4"
    ],
    data_files = [],
    entry_points={"console_scripts": [
        "nix-visualize=nix_visualize.visualize_tree:main"
    ]}
)
