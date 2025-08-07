import io
import os
import sys
import csv
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path to import app.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import the FastAPI app and helper
from app import app, is_csv_or_tsv

client = TestClient(app)


def make_uploadfile(filename: str, content: bytes):
    from starlette.datastructures import UploadFile
    return UploadFile(filename=filename, file=io.BytesIO(content))


def test_is_csv_or_tsv_rejects_wrong_extension():
    uf = make_uploadfile("data.txt", b"a,b\n1,2\n")
    valid, info = is_csv_or_tsv(uf)
    assert not valid
    assert "Invalid file extension" in info


def test_is_csv_or_tsv_accepts_csv():
    uf = make_uploadfile("data.csv", b"a,b\n1,2\n")
    valid, info = is_csv_or_tsv(uf)
    assert valid and info == "csv"


def test_is_csv_or_tsv_accepts_tsv():
    uf = make_uploadfile("data.tsv", b"a\tb\n1\t2\n")
    valid, info = is_csv_or_tsv(uf)
    assert valid and info == "tsv"


def test_is_csv_or_tsv_invalid_format():
    uf = make_uploadfile("data.csv", b"a|b\n1|2\n")
    valid, info = is_csv_or_tsv(uf)
    assert not valid


def test_upload_rejects_large_file():
    big_content = b"a,b\n" + b"1,2\n" * (1024 * 1024 // 4 + 10)  # >1MB approx
    response = client.post(
        "/upload",
        files={"file": ("big.csv", big_content, "text/csv")},
    )
    assert response.status_code == 400
    assert "exceeds 1MB" in response.json()["detail"]


def test_upload_accepts_csv():
    content = b"a,b\n1,2\n"
    response = client.post(
        "/upload",
        files={"file": ("ok.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "ok.csv"
    assert data["format"] == "csv"


def test_upload_accepts_tsv():
    content = b"a\tb\n1\t2\n"
    response = client.post(
        "/upload",
        files={"file": ("ok.tsv", content, "text/tab-separated-values")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "ok.tsv"
    assert data["format"] == "tsv"


def test_upload_rejects_wrong_extension():
    content = b"a,b\n1,2\n"
    response = client.post(
        "/upload",
        files={"file": ("bad.txt", content, "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]
