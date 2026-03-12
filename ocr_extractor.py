import cv2
import pytesseract
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def normalize(line):
    line = line.lower()
    line = line.replace('/', '-').replace('_', '-')
    line = re.sub(r'\s+', ' ', line)
    return line

FIELDS = {
    "TOTAL": ["total", "total amount", "amount payable", "grand total", "final amount", "balance due","net amt"],
    "Bill No": ["b.no", "bill no", "receipt no", "rec no"],
    "DATE": ["date", "bill date", "invoice date", "purchase date"]
}

COMMON_FIELD_KEYWORDS = []
for key, values in FIELDS.items():
    COMMON_FIELD_KEYWORDS.extend(values)

COMMON_FIELD_KEYWORDS.extend(["invoice no", "invoice number","bill no"])
COMMON_FIELD_KEYWORDS = [normalize(k) for k in COMMON_FIELD_KEYWORDS]


def extract_fields(ocr_text):

    results = {}
    lines = ocr_text.split('\n')

    merchant_candidates = [
        line.strip() for line in lines[:5]
        if line.strip()
        and not re.search(r'\d', line)
        and not any(keyword in normalize(line) for keyword in COMMON_FIELD_KEYWORDS)
    ]

    if merchant_candidates:
        results['MERCHANT'] = merchant_candidates[0]

    invoice_pattern = re.compile(r'(invoice|bill\s*no|No\.?\s*[:\-]?\s*)(\w+)', re.IGNORECASE)

    for line in lines:
        match = invoice_pattern.search(line)
        if match:
            results["INVOICE_NO"] = match.group(2)
            break

    for line in lines:

        normalized_line = normalize(line)

        for field, keywords in FIELDS.items():

            if any(k in normalized_line for k in keywords):

                if field == "TOTAL":
                    matches = re.findall(r'\d+\.\d{1,2}|\d+', line)
                    if matches:
                        results[field] = matches[-1]

                if field == "DATE":
                    matches_date = re.findall(
                        r'\b(\d{1,2})[-\/](\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\/](\d{2,4})\b',
                        line,
                        re.IGNORECASE
                    )

                    if matches_date:
                        day, month, year = matches_date[0]
                        results[field] = f"{day}-{month}-{year}"

    amount = re.search(r'[\u20B9\$]\s?([\d,]+\.?\d*)', ocr_text)

    if amount:
        results["CURRENCY_AMOUNT"] = amount.group(1)

    return results


def process_image(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    text = pytesseract.image_to_string(thresh, config="--psm 6")

    data = extract_fields(text)

    return data