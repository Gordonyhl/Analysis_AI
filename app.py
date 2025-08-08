"""FastAPI application for validating and summarizing uploaded count table files.

Exposes a POST `/upload` endpoint that:
- accepts CSV/TSV files,
- auto-detects the delimiter,
- streams parsing with pandas,
- validates RNA-seq style count tables (numeric columns, non-numeric gene IDs, non-empty), and
- returns basic metadata and a small preview of the data.
"""

import io
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import Optional
import pandas as pd
import csv

# initialize the FastAPI app
app = FastAPI()

# Helper function to detect the delimiter
def detect_delimiter(sample: str) -> Optional[str]:
    """
    Detects the delimiter of a text sample.
    Args:
        sample: A string sample from the file.
    Returns:
        The detected delimiter (',' or '\t') or None if not detected.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',\t')
        return dialect.delimiter
    except csv.Error:
        # Fallback for files that might not be perfectly structured CSV/TSV
        # for the sniffer to work, e.g. single column files.
        if '\t' in sample:
            return '\t'
        if ',' in sample:
            return ','
        return None


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads and validates a count table file (CSV or TSV).

    This endpoint processes the file in a streaming fashion, making it suitable
    for large files. It auto-detects the delimiter and uses pandas for robust
    parsing and validation.

    Returns:
        A JSON response with the file's properties, including dimensions,
        a snippet of the data, and column data types.
    """
    # Read a sample from the stream for delimiter detection
    try:
        sample_bytes = await file.read(2048)  # Read a larger sample for better detection
        await file.seek(0)  # Reset the stream pointer
        sample_str = sample_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Only UTF-8 is supported.")

    delimiter = detect_delimiter(sample_str)
    if not delimiter:
        raise HTTPException(status_code=400, detail="Could not determine the delimiter. Please use a comma or tab-separated file.")

    try:
        # Process the file stream with pandas
        # We use an iterator to read the file in chunks, which is memory-efficient.
        df_iterator = pd.read_csv(file.file, sep=delimiter, chunksize=1000, index_col=0, encoding='utf-8')

        # Get the first chunk to perform validation
        df = next(df_iterator)

        # --- Validation for RNA-seq Count Tables ---
        # 1. Check if data is numeric (counts should be numbers)
        if not all(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns):
            raise HTTPException(status_code=422, detail="Data validation error: All count columns must be numeric.")

        # 2. Check for non-numeric index (gene IDs should be strings)
        if pd.api.types.is_numeric_dtype(df.index.dtype):
            raise HTTPException(status_code=422, detail="Data validation error: The first column (gene IDs) should not be numeric.")

        # 3. Check for empty dataframe
        if df.empty:
            raise HTTPException(status_code=422, detail="Data validation error: The file appears to be empty or incorrectly formatted.")

        # If validation passes, you could continue processing the rest of the chunks
        # For this example, we'll just return info from the first chunk.
        # To process the whole file:
        # for chunk in df_iterator:
        #     # process chunk
        # full_df = pd.concat([df] + list(df_iterator)) # This would load the whole file in memory

        return {
            "filename": file.filename,
            "format": "csv" if delimiter == "," else "tsv",
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "index_name": df.index.name,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "head": df.head().to_dict(orient='split')
        }

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error processing file: {e}")