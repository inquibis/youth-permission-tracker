"""
Youth Data Import Package

This package provides utilities for extracting youth data from PDFs and 
loading it into the youth-permission-tracker system.

Modules:
- extract_from_pdf: Extract data from YM Members.pdf and YW Directory.pdf
- load_youth_data: Load extracted data into the API
- loader_config: Configuration settings
"""

__version__ = "1.0.0"
__author__ = "Youth Permission Tracker Team"

__all__ = [
    "extract_from_pdf",
    "load_youth_data",
    "loader_config",
]
