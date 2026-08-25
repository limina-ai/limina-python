# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="limina-ai",
    version="1.0.4",
    author="Limina AI",
    description="Deterministic Trajectory Diagnostics & Automated Prompt Patching for Multi-Turn AI Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    keywords=[
        "ai-agents",
        "llmops",
        "trajectory-diagnostics",
        "hallucination-detection",
        "prompt-patching",
        "langchain",
        "openai",
        "state-space-dag",
        "cognitive-architecture"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    install_requires=[
        "gradio_client>=0.17.0",
        "pyyaml>=6.0"
    ],
    python_requires=">=3.8",
    include_package_data=True,
)