from ocr.trocr_engine import extract_text

text = extract_text("static/uploads/sample.png")
print("Extracted Text:")
print(text)
