from setuptools import setup, find_packages

setup(
    name="cinema-shelf",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "colorama"
    ],
    entry_points={
        "console_scripts": [
            "cinema-shelf=cli.py:cli",
        ],
    },
)
