#!/usr/bin/env python3
"""
Main entry point for Pickleball Session Manager GUI
"""

import sys
import os
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add parent directory to path to import python module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Pickleball Session Manager')
        parser.add_argument('--test', action='store_true', 
                          help='Enable test mode (15x accelerated timing)')
        args = parser.parse_args()
        
        logger.info(f"Starting application... (test mode: {args.test})")
        
        # Initialize time manager before importing GUI
        from python.time_manager import initialize_time_manager
        initialize_time_manager(test_mode=args.test)
        
        from python.gui import main
        logger.info("GUI module imported successfully")
        main()
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\n{'='*70}")
        print(f"ERROR: {error_msg}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

