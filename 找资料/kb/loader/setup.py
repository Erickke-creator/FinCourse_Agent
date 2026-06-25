"""Setup for kb-loader package."""
from setuptools import setup, find_packages

setup(
    name="kb_loader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.3",
        "numpy>=1.20",
    ],
    python_requires=">=3.8",
    description="Knowledge base loader for SME loan evaluation",
)
