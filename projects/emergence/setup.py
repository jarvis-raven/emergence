#!/usr/bin/env python3
"""
Emergence AI — Autonomous agent framework with memory palace architecture

Setup script for PyPI distribution.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements from room/requirements.txt if it exists
room_requirements = []
room_req_file = this_directory / "room" / "requirements.txt"
if room_req_file.exists():
    with open(room_req_file, "r", encoding="utf-8") as f:
        room_requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    # Package metadata
    name="emergence-ai",
    version="0.4.0",
    description="Autonomous agent framework with Nautilus memory palace architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    # Author information
    author="Emergence Contributors",
    author_email="emergence@example.com",  # TODO: Update with actual email
    
    # URLs
    url="https://github.com/your-org/emergence",  # TODO: Update with actual repo
    project_urls={
        "Bug Tracker": "https://github.com/your-org/emergence/issues",
        "Documentation": "https://emergence.readthedocs.io",  # TODO: If applicable
        "Source Code": "https://github.com/your-org/emergence",
        "Changelog": "https://github.com/your-org/emergence/blob/main/CHANGELOG.md",
    },
    
    # License
    license="MIT",  # TODO: Verify license
    
    # Classifiers for PyPI
    classifiers=[
        # Development status
        "Development Status :: 4 - Beta",
        
        # Intended audience
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        
        # Topics
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        
        # License (must match license field)
        "License :: OSI Approved :: MIT License",
        
        # Python versions
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        
        # OS
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        
        # Framework
        "Framework :: Flask",
    ],
    
    # Keywords for discoverability
    keywords=[
        "ai",
        "agent",
        "autonomous",
        "memory",
        "nautilus",
        "knowledge-management",
        "semantic-search",
        "artificial-intelligence",
        "llm",
        "agents",
    ],
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Packages to include
    packages=find_packages(
        include=["core", "core.*", "room", "room.*"],
        exclude=["tests", "tests.*", "docs", "*.tests", "*.tests.*"]
    ),
    
    # Package data (non-Python files)
    package_data={
        "room": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
            "requirements.txt",
            "README.md",
        ],
        "core.nautilus": [
            "*.md",
        ],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=[
        # Core dependencies (minimal for Nautilus)
        # No heavy dependencies - Nautilus is lightweight
    ],
    
    # Optional dependencies (extras_require)
    extras_require={
        # Room web dashboard dependencies
        "room": room_requirements if room_requirements else [
            "flask>=2.3.0,<4.0.0",
            "flask-socketio>=5.3.0,<6.0.0",
            "flask-cors>=4.0.0,<5.0.0",
        ],
        
        # Development dependencies
        "dev": [
            "pytest>=7.0.0",
            "pytest-timeout>=2.1.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        
        # Documentation dependencies
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "pdoc3>=0.10.0",
        ],
    },
    
    # Console scripts / entry points
    entry_points={
        "console_scripts": [
            "emergence=core.cli:main",
            "nautilus=core.nautilus.cli:main",
        ],
    },
    
    # Additional metadata
    zip_safe=False,  # Don't install as a zip file
)
