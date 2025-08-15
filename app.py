"""FastAPI application with chat interface and file upload functionality."""

import os
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import router as chat_router

# initialize the FastAPI app
app = FastAPI()

# Include the chat router from api.py
app.include_router(chat_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure uploads directory exists
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)


@app.get("/")
async def read_root():
    """Serve the main index.html file."""
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Simple file upload endpoint that saves files to the uploads/ directory.
    
    Returns:
        A JSON response confirming the file was uploaded successfully.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save the file to the uploads directory
    file_path = uploads_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "message": f"File '{file.filename}' uploaded successfully",
            "filename": file.filename,
            "status": "success"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")