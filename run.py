#!/usr/bin/env python3
"""
MKCode - AI Agent Platform
Entry point for running the application.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
