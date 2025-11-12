#!/usr/bin/env python3
"""
Debug launcher for Pickleball Session Manager
Shows errors and tracebacks clearly
"""

import sys
import os
import logging
from traceback import format_exc

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

try:
    logger.info("Starting Pickleball Session Manager...")
    
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    logger.info("Python path configured")
    logger.info(f"Python version: {sys.version}")
    
    # Import PyQt6
    logger.info("Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication, QMessageBox
    logger.info("PyQt6 imported successfully")
    
    # Import GUI
    logger.info("Importing GUI module...")
    from python.gui import MainWindow
    logger.info("GUI module imported successfully")
    
    # Create application
    logger.info("Creating QApplication...")
    app = QApplication(sys.argv)
    
    # Create and show main window
    logger.info("Creating MainWindow...")
    window = MainWindow()
    window.show()
    
    logger.info("MainWindow shown, starting event loop...")
    sys.exit(app.exec())
    
except ImportError as e:
    error_msg = f"Import Error: {str(e)}\n\nTraceback:\n{format_exc()}"
    print(f"\n{'='*70}")
    print("IMPORT ERROR")
    print(f"{'='*70}")
    print(error_msg)
    print(f"{'='*70}\n")
    logger.error(error_msg)
    sys.exit(1)
    
except Exception as e:
    error_msg = f"Fatal Error: {str(e)}\n\nTraceback:\n{format_exc()}"
    print(f"\n{'='*70}")
    print("FATAL ERROR")
    print(f"{'='*70}")
    print(error_msg)
    print(f"{'='*70}\n")
    logger.error(error_msg)
    sys.exit(1)
