# OCR Expense Backend

Extract bill/invoice fields (merchant, total, date, tax, etc.) from images or camera capture using Tesseract OCR.

## Setup

```bash
# 1. Install Tesseract OCR
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Linux:   sudo apt install tesseract-ocr
# macOS:   brew install tesseract

# 2. Update path in ocr_extractor.py if needed:
#    pytesseract.pytesseract.tesseract_cmd = r"path\to\tesseract.exe"

# 3. Install Python deps
pip install -r requirements.txt

# 4. Run
uvicorn main1:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Endpoint        | Description                  |
|--------|-----------------|------------------------------|
| GET    | `/`             | API info                     |
| GET    | `/health`       | Health check                 |
| POST   | `/scan-bill/`   | Upload image file            |
| POST   | `/scan-camera/` | Send base64 image from camera|

### `/scan-bill/` — Upload image

```bash
curl -X POST -F "file=@bill.jpg" http://localhost:8000/scan-bill/
```

### `/scan-camera/` — Base64 image

```json
POST /scan-camera/
{
  "image": "<base64_encoded_image_data>"
}
```

## Response

```json
{
  "status": "success",
  "merchant": "Store Name",
  "invoice_no": "12345",
  "total": "1500.00",
  "subtotal": "1350.00",
  "tax": "150.00",
  "date": "15-Jan-2025",
  "category": "Office Supplies",
  "gst_no": "27AABCU9603R1ZN",
  "currency_amount": "1500.00",
  "confidence": "high"
}
```

## Frontend Integration

For camera capture on the frontend (web/mobile), send the base64 image string to `POST /scan-camera/`.
