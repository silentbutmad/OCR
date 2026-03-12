from fastapi import FastAPI, UploadFile, File
import shutil
import os
from ocr_extractor import process_image

app = FastAPI()

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.get("/")
def home():
    return {"message": "OCR Expense API Running"}


@app.post("/scan-bill/")
async def scan_bill(file: UploadFile = File(...)):

    file_path = f"{UPLOAD_FOLDER}/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Call OCR
    extracted_data = process_image(file_path)

    return {
        "status": "success",
        "extracted_data": extracted_data
    }