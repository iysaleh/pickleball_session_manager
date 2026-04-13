"""Test configuration: ensure the project root is on sys.path so that
``from python.<module>`` imports work regardless of how tests are invoked."""

import os
import sys

# Project root is one level up from this file's directory
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
