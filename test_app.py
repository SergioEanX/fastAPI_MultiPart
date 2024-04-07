import pytest
import httpx
import tempfile
import uvicorn
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
from fastapi.testclient import TestClient
from main import app  # replace with the name of your FastAPI app file

client = TestClient(app)

# https://github.com/tiangolo/fastapi/issues/1536
# TODO: Fix the test_upload_data_and_file() test
def test_upload_data_and_file():
    # Open a file in binary mode
    file_path = Path("./Excel_Files/test.xlsx")
    with open(file_path, "rb") as file:
        # Create an instance of UploadFile
        upload_file = UploadFile(file_path.name)
        upload_file.file = file

        # Define the JSON data to be sent in the request
        data = {"user_email": "ferlito.sergio@gmail.com", "institution": "NA"}

        # Make a POST request to the /upload_data_and_file/ endpoint with the test file and JSON data
        response = client.post("/upload", data=data, files={"excel_file": upload_file})

    # Assert that the response status code is 200 (OK)
    assert response.status_code == 200

    # Assert that the response JSON contains the expected data
    assert response.json() == {"message": "Data and file saved successfully!"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Uvicorn version: ": uvicorn.__version__, "time": datetime.now().strftime("%Y-%m-%d "
                                                                                                         "%H:%M:%S")}
