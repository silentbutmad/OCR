import cv2
import pytesseract
import re
from tkinter import Tk, filedialog
# -------------------------
# Configure Tesseract Path
# -------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------
# Normalize OCR Text
# -------------------------
def normalize(line):
    line = line.lower()
    line = line.replace('/', '-').replace('_', '-')
    line = re.sub(r'\s+', ' ', line)
    return line

# -------------------------
# Field Synonyms
# -------------------------
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

# -------------------------
# Extract Fields
# -------------------------
def extract_fields(ocr_text):

    results = {}
    lines = ocr_text.split('\n')

    # Merchant Detection
    merchant_candidates = [
        line.strip() for line in lines[:5]
        if line.strip()
        and not re.search(r'\d', line)
        and not any(keyword in normalize(line) for keyword in COMMON_FIELD_KEYWORDS)
    ]

    if merchant_candidates:
        results['MERCHANT'] = merchant_candidates[0]

    # Invoice Number
    invoice_pattern = re.compile(r'(invoice|Invoice|bill\s*no|No\.?\s*[:\-]?\s*)(\w+)', re.IGNORECASE)

    for line in lines:
        match = invoice_pattern.search(line)
        if match:
            results["INVOICE_NO"] = match.group(2)
            break

    # Line Processing
    for line in lines:

        normalized_line = normalize(line)

        for field, keywords in FIELDS.items():

            if any(k in normalized_line for k in keywords):

                # Amount
                if field == "TOTAL":
                    matches = re.findall(r'\d+\.\d{1,2}|\d+', line)
                    if matches:
                        results[field] = matches[-1]

                # Date
                if field == "DATE":

                    matches_date = re.findall(
                        r'\b(\d{1,2})[-\/](\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\/](\d{2,4})\b',
                        line,
                        re.IGNORECASE
                    )

                    if matches_date:
                        day, month, year = matches_date[0]
                        results[field] = f"{day}-{month}-{year}"

    # Currency Detection
    amount = re.search(r'[\u20B9\$]\s?([\d,]+\.?\d*)', ocr_text)

    if amount:
        results["CURRENCY_AMOUNT"] = amount.group(1)

    return results


# -------------------------
# Image Processing + OCR
# -------------------------
def process_image(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(
        gray,
        150,
        255,
        cv2.THRESH_BINARY,
    )[1]

    text = pytesseract.image_to_string(thresh, config="--psm 6")

    print("\nExtracted OCR Text\n")
    print(text)

    data = extract_fields(text)

    print("\nExtracted Fields\n")
    print(data)


# -------------------------
# Camera Capture
# -------------------------
def capture_from_camera():

    cap = cv2.VideoCapture(0)

    print("Press 's' to scan bill")
    print("Press 'q' to quit")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1)

        if key == ord('s'):

            print("\nScanning bill...\n")

            process_image(frame)

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# -------------------------
# Upload Image
# -------------------------
def upload_image():

    # Hide main tkinter window
    root = Tk()
    root.withdraw()

    # Open file selection dialog
    file_path = filedialog.askopenfilename(
        title="Select Bill Image",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
    )

    if not file_path:
        print("No image selected")
        return

    image = cv2.imread(file_path)

    if image is None:
        print("Invalid image")
        return

    cv2.imshow("Selected Image", image)
    cv2.waitKey(2000)

    print("\nProcessing image...\n")

    process_image(image)

    cv2.destroyAllWindows()


# -------------------------
# Main Menu
# -------------------------
while True:

    print("\n====== BILL OCR SYSTEM ======")
    print("1 → Capture from Camera")
    print("2 → Upload Image")
    print("3 → Exit")

    choice = input("Enter choice: ")

    if choice == "1":
        capture_from_camera()

    elif choice == "2":
        upload_image()

    elif choice == "3":
        print("Exiting...")
        break

    else:
        print("Invalid choice")