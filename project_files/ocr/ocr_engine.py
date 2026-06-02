import cv2
import pytesseract
from PIL import Image

# 👉 IMPORTANT (Windows users)
# Uncomment and update this path if Tesseract is not in PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(image_path):
    """
    Improves image quality for better OCR
    """
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError("Image not found or unable to read image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return thresh


def extract_text(image_path):
    """
    Takes image path and returns extracted text
    """
    processed_img = preprocess_image(image_path)

    pil_img = Image.fromarray(processed_img)

    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(pil_img, config=custom_config)

    return text
