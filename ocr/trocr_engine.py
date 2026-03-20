from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import pytesseract
import cv2
import torch
import numpy as np
import os
import platform

# Tesseract setup
if platform.system() == "Windows":
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
# On Linux (Render/Docker), it should be in the PATH automatically

# TrOCR setup
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
device = torch.device("cpu")
model.to(device)

def trocr_extract(image):
    image = image.resize((384, 384))
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
    generated_ids = model.generate(pixel_values, max_length=64)
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

def extract_text(image_path):
    """
    Hybrid OCR: Tesseract + TrOCR
    """

    # ---- TESSERACT (full page) ----
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tesseract_text = pytesseract.image_to_string(gray)

    # ---- TrOCR (handwriting emphasis) ----
    pil_img = Image.open(image_path).convert("RGB")
    trocr_text = trocr_extract(pil_img)

    # ---- Combine results ----
    final_text = tesseract_text + "\n" + trocr_text

    return final_text
