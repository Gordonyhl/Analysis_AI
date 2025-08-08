import io
import os
import sys
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


def test_upload_rejects_non_numeric_columns():
    content = (
        b"gene,s1,s2\n"
        b"G1,1,foo\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("bad.csv", content, "text/csv")},
    )
    assert response.status_code == 422
    assert "All count columns must be numeric" in response.json()["detail"]


def test_upload_rejects_numeric_index():
    content = (
        b"gene,s1\n"
        b"1,2\n"
        b"2,3\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("bad.csv", content, "text/csv")},
    )
    assert response.status_code == 422
    assert "should not be numeric" in response.json()["detail"]


def test_upload_rejects_empty_file():
    content = b"\n"
    response = client.post(
        "/upload",
        files={"file": ("empty.csv", content, "text/csv")},
    )
    # With no comma/tab present, delimiter detection fails → 400
    assert response.status_code == 400
    assert "Could not determine the delimiter" in response.json()["detail"]
