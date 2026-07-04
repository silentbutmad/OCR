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
import logging
from ocr_extractor import process_image, process_image_array

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    logger.info("=" * 50)
    logger.info("Received scan-bill request")
    logger.debug(f"File name: {file.filename}")
    logger.debug(f"File content type: {file.content_type}")

    print("m=================================")
    print("m=================================")
    print("m=================================")
    print("m=================================")
    print("=" * 50)
    print("Filename:", file.filename)
    print("Content Type:", file.content_type)
    print("File Size:", len(contents))
    print("MD5:", hashlib.md5(contents).hexdigest())
    print("=" * 50)



    # Validate file extension instead of content-type (more reliable)
    if file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif']
        if file_ext not in allowed_extensions:
            logger.error(f"Invalid file extension: {file_ext}")
            raise HTTPException(400, detail=f"File must be an image. Allowed formats: {', '.join(allowed_extensions)}")
        logger.debug(f"File extension validated: {file_ext}")
    else:
        logger.error("No filename provided")
        raise HTTPException(400, detail="File must have a filename")

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    try:
        logger.debug(f"Saving file to: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved successfully, validating image...")
        
        # Validate that the file is actually a readable image
        test_img = cv2.imread(file_path)
        if test_img is None:
            logger.error("File is not a valid image or is corrupted")
            raise HTTPException(400, detail="Invalid image file. Please upload a valid image.")
        
        logger.debug(f"Image validated successfully: shape={test_img.shape}")
        
        logger.info(f"Processing with OCR...")
        data = process_image(file_path)
        logger.info(f"OCR processing completed: {data}")
        
        response = map_response(data)
        logger.info(f"Response: {response}")
        logger.info("=" * 50)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing bill: {type(e).__name__} - {str(e)}", exc_info=True)
        logger.info("=" * 50)
        raise HTTPException(500, detail=f"Error processing image: {str(e)}")
    finally:
        if os.path.exists(file_path):
            logger.debug(f"Cleaning up temporary file: {file_path}")
            os.remove(file_path)

class CameraPayload(BaseModel):
    image: str

@app.post("/ocr/scan-camera/", response_model=OCRResponse)
async def scan_camera(payload: CameraPayload):
    logger.info("=" * 50)
    logger.info("Received scan-camera request")
    logger.debug(f"Payload image length: {len(payload.image)}")
    logger.debug(f"Payload image preview (first 100 chars): {payload.image[:100]}")
    
    try:
        # Decode base64 image
        logger.debug("Decoding base64 image...")
        image_data = base64.b64decode(payload.image)
        logger.debug(f"Decoded image size: {len(image_data)} bytes")
        
        np_arr = np.frombuffer(image_data, np.uint8)
        logger.debug(f"NumPy array shape: {np_arr.shape}")
        
        # Use IMREAD_UNCHANGED to preserve alpha channel for PNG files
        logger.debug("Decoding image with cv2.imdecode (IMREAD_UNCHANGED)...")
        img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)
        
        if img is None:
            logger.error("cv2.imdecode returned None - invalid image data")
            raise HTTPException(400, detail="Invalid image data: Could not decode image")
        
        logger.debug(f"Image shape: {img.shape}, dtype: {img.dtype}")
        logger.info(f"Image decoded successfully: {img.shape}")
        
        # Handle PNG with alpha channel (4 channels: BGRA)
        if len(img.shape) == 3 and img.shape[2] == 4:
            logger.info("Detected 4-channel BGRA image (PNG with alpha), converting to BGR")
            # Convert BGRA to BGR by removing alpha channel
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            logger.debug(f"Converted to BGR, new shape: {img.shape}")
        # Handle grayscale images (1 channel)
        elif len(img.shape) == 2:
            logger.info("Detected grayscale image, converting to BGR")
            # Convert grayscale to BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            logger.debug(f"Converted to BGR, new shape: {img.shape}")
        else:
            logger.debug(f"Image already in BGR format: {img.shape}")

        # Process image with OCR
        logger.info("Starting OCR processing...")
        data = process_image_array(img)
        logger.info(f"OCR processing completed: {data}")
        
        response = map_response(data)
        logger.info(f"Response: {response}")
        logger.info("=" * 50)
        return response
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.status_code} - {he.detail}")
        logger.info("=" * 50)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__} - {str(e)}", exc_info=True)
        logger.info("=" * 50)
        raise HTTPException(500, detail=f"Internal server error: {str(e)}")
