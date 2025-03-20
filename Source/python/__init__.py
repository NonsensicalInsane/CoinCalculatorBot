# This file makes the directory a Python package 

"""
Main package initialization for the CoinCalculatorBot.
This helps Python correctly resolve imports within the package.
"""

import os
import sys

# Add the parent directory to the Python path if it's not already there
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir) 