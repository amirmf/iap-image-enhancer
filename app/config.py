"""Configuration for the application."""
import os
import platform

# Tesseract executable path
if platform.system() == 'Windows':
    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    TESSERACT_CMD = 'tesseract'  # Assumes it's in PATH on Linux/Mac

# Set it globally for pytesseract
import pytesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD