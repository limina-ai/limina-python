# setup.py
from setuptools import setup, find_packages

setup(
    name="limina-monitor",
    version="0.1.0",
    description="Python client SDK for multi-turn AI Agent evaluation & trajectory monitoring with Limina AI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Limina AI",
    url="https://github.com/limina-ai/limina-python",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)