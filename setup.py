#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="skywire",
    version="0.1.0",
    description="Distributed Audio Routing System",
    author="Jay Brame",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "aiohttp>=3.8.0",
        "websockets>=11.0",
        "pyyaml>=6.0",
        "numpy>=1.20.0",
        "jinja2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "skywire=skywire.__main__:run",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
