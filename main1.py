from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from eureka_client import register
import shutil
import os
import base64
import numpy as np
import cv2
from ocr_extractor import process_image, process_image_array

app = FastAPI(title="OCR Expense Backend", version="2.0.0")

@app.on_event("startup")
async def startup():
    await register()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class OCRResponse(BaseModel):
    status: str
    merchant: Optional[str] = None
    invoice_no: Optional[str] = None
    total: Optional[str] = None
    subtotal: Optional[str] = None
    tax: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None
    gst_no: Optional[str] = None
    currency_amount: Optional[str] = None
    confidence: Optional[str] = None
    error: Optional[str] = None

def map_response(data: dict) -> OCRResponse:
    return OCRResponse(
        status=data.get("status", "failed"),
        merchant=data.get("MERCHANT"),
        invoice_no=data.get("INVOICE_NO") or data.get("Bill No"),
        total=data.get("TOTAL"),
        subtotal=data.get("SUBTOTAL"),
        tax=data.get("TAX"),
        date=data.get("DATE"),
        category=data.get("CATEGORY"),
        gst_no=data.get("GST_NO"),
        currency_amount=data.get("CURRENCY_AMOUNT"),
        confidence=data.get("confidence"),
        error=data.get("error"),
    )


@app.get("/")
@app.get("/ocr")
def home():
    return {
        "message": "OCR Expense API Running",
        "version": "2.0.0",
        "endpoints": {
            "POST /scan-bill/": "Upload an image file",
            "POST /scan-camera/": "Send base64 image from camera",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr/scan-bill/", response_model=OCRResponse)
async def scan_bill(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="File must be an image")

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        data = process_image(file_path)
        return map_response(data)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

class CameraPayload(BaseModel):
    image: str

@app.post("/ocr/scan-camera/", response_model=OCRResponse)
async def scan_camera(payload: CameraPayload):
    try:
        image_data = base64.b64decode(payload.image)
        np_arr = np.frombuffer(image_data, np.uint8)
        
        # Use IMREAD_UNCHANGED to preserve alpha channel for PNG files
        img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise HTTPException(400, detail="Invalid image data")
        
        # Handle PNG with alpha channel (4 channels: BGRA)
        if len(img.shape) == 3 and img.shape[2] == 4:
            # Convert BGRA to BGR by removing alpha channel
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # Handle grayscale images (1 channel)
        elif len(img.shape) == 2:
            # Convert grayscale to BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        data = process_image_array(img)
        return map_response(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))
