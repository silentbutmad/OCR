import cv2
import pytesseract
import re
import numpy as np
import os
import platform

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

def normalize(line):
    line = line.lower()
    line = line.replace('/', '-').replace('_', '-')
    line = re.sub(r'\s+', ' ', line)
    return line.strip()

FIELDS = {
    "TOTAL": ["total", "total amount", "amount payable", "grand total",
              "final amount", "balance due", "net amt", "net amount",
              "payable", "to pay", "amount due"],
    "SUBTOTAL": ["subtotal", "sub total"],
    "TAX": ["tax", "gst", "vat", "cgst", "sgst", "igst", "tax amount"],
    "Bill No": ["b.no", "bill no", "receipt no", "rec no", "invoice no",
                "invoice number", "inv no", "inv #", "receipt #"],
    "DATE": ["date", "bill date", "invoice date", "purchase date",
             "transaction date", "txn date"],
    "CATEGORY": ["category", "type", "expense type", "nature of expense"]
}

COMMON_FIELD_KEYWORDS = []
for key, values in FIELDS.items():
    COMMON_FIELD_KEYWORDS.extend(values)
COMMON_FIELD_KEYWORDS = [normalize(k) for k in COMMON_FIELD_KEYWORDS]


def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    kernel = np.ones((1, 1), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    return thresh


def extract_fields(ocr_text):
    results = {"confidence": "medium"}
    lines = ocr_text.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]

    merchant_candidates = [
        line.strip() for line in non_empty_lines[:7]
        if line.strip()
        and not re.search(r'\d', line)
        and len(line.strip()) > 2
        and not any(keyword in normalize(line) for keyword in COMMON_FIELD_KEYWORDS)
    ]
    if merchant_candidates:
        results['MERCHANT'] = merchant_candidates[0]

    gst_pattern = re.compile(
        r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
    )
    for line in lines:
        match = gst_pattern.search(line.upper())
        if match:
            results["GST_NO"] = match.group(0)
            break

    invoice_pattern = re.compile(
        r'(?:invoice|bill|receipt|inv|rec)\s*(?:no|#|number|num)?\s*[:\-]?\s*([A-Za-z0-9\-/]+)',
        re.IGNORECASE
    )
    for line in lines:
        match = invoice_pattern.search(line)
        if match:
            results["INVOICE_NO"] = match.group(1).strip()
            break

    for line in lines:
        normalized_line = normalize(line)

        for field, keywords in FIELDS.items():
            if any(k in normalized_line for k in keywords):
                if field in ("TOTAL", "SUBTOTAL", "TAX"):
                    matches = re.findall(r'\d+\.\d{1,2}', line)
                    if not matches:
                        matches = re.findall(r'\d+', line)
                    if matches:
                        results[field] = matches[-1]

                if field == "DATE":
                    date_patterns = [
                        r'\b(\d{1,2})[-\/](\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\/](\d{2,4})\b',
                        r'\b(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})\b'
                    ]
                    for pat in date_patterns:
                        matches_date = re.findall(pat, line, re.IGNORECASE)
                        if matches_date:
                            parts = matches_date[0]
                            if len(parts[0]) == 4:
                                results[field] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                            else:
                                day, month, year = parts
                                if not month.isdigit():
                                    month = month.capitalize()
                                results[field] = f"{day}-{month}-{year}"
                            break

                if field == "CATEGORY":
                    parts = re.split(r'[:\-]\s*', line, maxsplit=1)
                    if len(parts) > 1:
                        results[field] = parts[1].strip()

    amount = re.search(r'[\u20B9$]\s?([\d,]+\.?\d*)', ocr_text)
    if amount:
        results["CURRENCY_AMOUNT"] = amount.group(1)

    if results.get("TOTAL") and results.get("SUBTOTAL") and results.get("TAX"):
        try:
            sub = float(results["SUBTOTAL"])
            tax = float(results["TAX"])
            total = float(results["TOTAL"])
            if abs((sub + tax) - total) < 1.0:
                results["confidence"] = "high"
        except ValueError:
            pass

    return results


def process_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return {"error": f"Cannot read image at {image_path}", "status": "failed"}

    processed = preprocess_image(image)
    text = pytesseract.image_to_string(processed, config="--psm 6 --oem 3")

    data = extract_fields(text)
    data["status"] = "success"
    return data


def process_image_array(image_array):
    processed = preprocess_image(image_array)
    text = pytesseract.image_to_string(processed, config="--psm 6 --oem 3")

    data = extract_fields(text)
    data["status"] = "success"
    return data
