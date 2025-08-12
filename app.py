import csv
import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List

# initialize the FastAPI app
app = FastAPI()

def is_csv_or_tsv(file: UploadFile) -> (bool, str):
    """
    Checks if the uploaded file is in CSV or TSV format.

    Args:
        file: The uploaded file.

    Returns:
        A tuple containing a boolean indicating if the file is valid
        and a string with the detected format or an error message.
    """
    filename = file.filename
    if not (filename.endswith('.csv') or filename.endswith('.tsv')):
        return False, "Invalid file extension. Please upload a .csv or .tsv file."

    try:
        # Read a sample of the file to determine the dialect
        content = file.file.read(1024).decode('utf-8')
        file.file.seek(0)  # Reset the file pointer

        dialect = csv.Sniffer().sniff(content)

        if dialect.delimiter == ',':
            return True, "csv"
        elif dialect.delimiter == '\t':
            return True, "tsv"
        else:
            return False, "File is not in a valid CSV or TSV format."

    except (csv.Error, UnicodeDecodeError):
        return False, "Could not determine the file format. Please ensure it is a valid CSV or TSV."



@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # check file size
    contents = await file.read()
    if len(contents) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 1MB")

    # Reset file pointer after reading contents
    await file.seek(0)

    # Validate CSV/TSV format using existing helper
    is_valid, info = is_csv_or_tsv(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=info)

    # Optionally, you could proceed to process 'file.file' stream here.
    # Make sure the pointer is at start for any downstream readers.
    file.file.seek(0)

    return {"filename": file.filename, "format": info}