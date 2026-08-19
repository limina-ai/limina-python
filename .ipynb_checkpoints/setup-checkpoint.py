from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="limina-ai",
    version="1.0.1",
    author="Limina AI",
    description="Deterministic Trajectory Diagnostics & Automated Prompt Patching for AI Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Quality Assurance",
    ],
    install_requires=[
        "gradio_client>=0.17.0"
    ],
    python_requires=">=3.8",
)