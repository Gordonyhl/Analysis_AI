import io
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Ensure project root is on sys.path to import app.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import the FastAPI app
from app import app

client = TestClient(app)


def test_upload_accepts_csv_count_table():
    content = (
        b"gene,s1,s2\n"
        b"G1,1,2\n"
        b"G2,3,4\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("ok.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "ok.csv"
    assert data["format"] == "csv"
    assert data["shape"] == [2, 2]
    assert data["columns"] == ["s1", "s2"]
    assert data["index_name"] == "gene"


def test_upload_accepts_tsv_count_table():
    content = (
        b"gene\ts1\ts2\n"
        b"G1\t1\t2\n"
        b"G2\t3\t4\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("ok.tsv", content, "text/tab-separated-values")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "ok.tsv"
    assert data["format"] == "tsv"
    assert data["shape"] == [2, 2]
    assert data["columns"] == ["s1", "s2"]
    assert data["index_name"] == "gene"


def test_upload_rejects_unknown_delimiter():
    content = (
        b"gene|s1|s2\n"
        b"G1|1|2\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("bad.txt", content, "text/plain")},
    )
    assert response.status_code == 400
    assert "Could not determine the delimiter" in response.json()["detail"]


def test_upload_accepts_mixed_data_types():
    """Test that the app accepts files with mixed data types (no validation for numeric columns)."""
    content = (
        b"gene,s1,s2\n"
        b"G1,1,foo\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("mixed.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "mixed.csv"
    assert data["format"] == "csv"


def test_upload_accepts_numeric_index():
    """Test that the app accepts files with numeric indices (no validation against numeric indices)."""
    content = (
        b"gene,s1\n"
        b"1,2\n"
        b"2,3\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("numeric_index.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "numeric_index.csv"
    assert data["format"] == "csv"


def test_upload_rejects_empty_file():
    content = b"\n"
    response = client.post(
        "/upload",
        files={"file": ("empty.csv", content, "text/csv")},
    )
    # With no comma/tab present, delimiter detection fails → 400
    assert response.status_code == 400
    assert "Could not determine the delimiter" in response.json()["detail"]


def test_upload_rejects_invalid_file_extension():
    """Test that the app rejects files with invalid extensions."""
    content = b"gene,s1,s2\nG1,1,2\n"
    response = client.post(
        "/upload",
        files={"file": ("document.pdf", content, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
    
    # Test another invalid extension
    response = client.post(
        "/upload",
        files={"file": ("document.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_accepts_txt_file():
    """Test that the app accepts valid TXT files with tab delimiter."""
    content = (
        b"gene\ts1\ts2\n"
        b"G1\t1\t2\n"
        b"G2\t3\t4\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("data.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "data.txt"
    assert data["format"] == "tsv"
    assert data["shape"] == [2, 2]
    assert data["columns"] == ["s1", "s2"]
    assert data["index_name"] == "gene"


def test_upload_rejects_invalid_encoding():
    """Test that the app rejects files with invalid UTF-8 encoding."""
    # Create content with invalid UTF-8 bytes
    content = b"gene,s1,s2\nG1,1,2\n\xff\xfe"  # Adding invalid UTF-8 bytes
    response = client.post(
        "/upload",
        files={"file": ("bad_encoding.csv", content, "text/csv")},
    )
    assert response.status_code == 400
    assert "Invalid file encoding" in response.json()["detail"]


def test_upload_returns_complete_metadata():
    """Test that the response contains all expected metadata fields."""
    content = (
        b"gene,sample1,sample2\n"
        b"GENE1,10,20\n"
        b"GENE2,30,40\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("complete.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check all expected fields are present
    expected_fields = ["filename", "format", "shape", "columns", "index_name", "dtypes", "head"]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"
    
    # Verify field values
    assert data["filename"] == "complete.csv"
    assert data["format"] == "csv"
    assert data["shape"] == [2, 2]  # 2 rows, 2 columns (excluding index)
    assert data["columns"] == ["sample1", "sample2"]
    assert data["index_name"] == "gene"
    assert isinstance(data["dtypes"], dict)
    assert isinstance(data["head"], dict)
    assert "data" in data["head"]  # pandas split format includes "data" key


def test_upload_handles_totally_empty_dataframe():
    """Test that the app handles files that result in completely empty dataframes."""
    # Create content that results in empty dataframe after parsing
    content = b"   \n   \n   \n"  # Just whitespace
    response = client.post(
        "/upload",
        files={"file": ("empty_data.csv", content, "text/csv")},
    )
    # Should fail at delimiter detection step
    assert response.status_code == 400
    assert "Could not determine the delimiter" in response.json()["detail"]


def test_delimiter_detection_edge_cases():
    """Test delimiter detection with edge cases."""
    # Test file with only commas (single column after splitting)
    content = b"gene\nGENE1\nGENE2\n"
    response = client.post(
        "/upload",
        files={"file": ("single_col.csv", content, "text/csv")},
    )
    # This should fail delimiter detection since there are no delimiters
    assert response.status_code == 400
    assert "Could not determine the delimiter" in response.json()["detail"]
    
    # Test file with tabs but labeled as CSV
    content = b"gene\ts1\nGENE1\t100\n"
    response = client.post(
        "/upload",
        files={"file": ("tab_file.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "tsv"  # Should detect tab delimiter


def test_upload_handles_large_file_structure():
    """Test that the app can handle the structure expected for chunked reading."""
    # Create content that represents a larger file structure
    lines = [b"gene,s1,s2,s3"]
    for i in range(50):  # Create 50 data rows
        lines.append(f"GENE{i:03d},10,20,30".encode())
    content = b"\n".join(lines) + b"\n"
    
    response = client.post(
        "/upload",
        files={"file": ("large.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "large.csv"
    assert data["format"] == "csv"
    assert data["shape"][0] == 50  # 50 rows
    assert data["shape"][1] == 3   # 3 columns
    assert len(data["columns"]) == 3


# ========== Tests for /api/threads endpoint ==========

@patch('storage.get_all_threads')
def test_list_threads_empty(mock_get_all_threads):
    """Test /api/threads endpoint returns empty list when no threads exist."""
    # Mock the storage function to return empty list
    mock_get_all_threads.return_value = []
    
    response = client.get("/api/threads")
    assert response.status_code == 200
    data = response.json()
    assert data == []
    assert isinstance(data, list)


@patch('storage.get_all_threads')
def test_list_threads_with_data(mock_get_all_threads):
    """Test /api/threads endpoint returns list of threads when threads exist."""
    # Mock data that matches the Thread model structure
    mock_threads = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Test Thread 1",
            "created_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001", 
            "title": "Test Thread 2",
            "created_at": "2024-01-14T09:20:00Z"
        }
    ]
    mock_get_all_threads.return_value = mock_threads
    
    response = client.get("/api/threads")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert isinstance(data, list)
    
    # Check first thread
    assert data[0]["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data[0]["title"] == "Test Thread 1"
    assert data[0]["created_at"] == "2024-01-15T10:30:00Z"
    
    # Check second thread
    assert data[1]["id"] == "550e8400-e29b-41d4-a716-446655440001"
    assert data[1]["title"] == "Test Thread 2"
    assert data[1]["created_at"] == "2024-01-14T09:20:00Z"


@patch('storage.get_all_threads')
def test_list_threads_storage_exception(mock_get_all_threads):
    """Test /api/threads endpoint handles storage exceptions gracefully."""
    # Mock the storage function to raise an exception
    mock_get_all_threads.side_effect = Exception("Database connection error")
    
    response = client.get("/api/threads")
    # FastAPI will return 500 for unhandled exceptions
    assert response.status_code == 500


def test_list_threads_endpoint_exists():
    """Test that the /api/threads endpoint exists and accepts GET requests."""
    # This test doesn't mock storage, so it will use real database
    # It should at least not return 404 (endpoint exists)
    response = client.get("/api/threads")
    # Should be 200 (success) or 500 (if database not set up), but not 404
    assert response.status_code != 404
    assert response.status_code in [200, 500]


def test_list_threads_response_format():
    """Test that /api/threads endpoint returns properly formatted JSON."""
    response = client.get("/api/threads")
    
    # Should return valid JSON regardless of data
    assert response.headers["content-type"] == "application/json"
    
    # Response should be parseable as JSON
    data = response.json()
    assert isinstance(data, list)  # Should always be a list
