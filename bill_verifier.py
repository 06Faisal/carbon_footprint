import pytesseract
from PIL import Image
import cv2
import re

# Change path if needed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_bill(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    text = pytesseract.image_to_string(gray)
    return text

def extract_units(text):
    patterns = [
        r'Units\s*Consumed\s*[:\-]?\s*(\d+)',
        r'Total\s*Units\s*[:\-]?\s*(\d+)',
        r'Energy\s*[:\-]?\s*(\d+)'
    ]

    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def verify_units(user_units, extracted_units):
    if extracted_units is None:
        return "❌ Could not detect units from bill"

    diff = abs(user_units - extracted_units)

    if diff == 0:
        return "✅ Perfect Match"
    elif diff <= 5:
        return "🟡 Very Close"
    else:
        return "❌ Mismatch — Please check your input"
