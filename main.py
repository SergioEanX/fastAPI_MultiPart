import string
import asyncio
import os
import uvicorn
from datetime import datetime
from random import choices
from pathlib import Path
from typing import Annotated, Type, Optional
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, UploadFile, Form, File, Depends, status, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from aiofiles import open as aio_open
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError

import logging

logger = logging.getLogger('main')
env = load_dotenv()
mongo_uri = os.getenv("uri")

# enable debug logging for the asyncio module
logger.setLevel(logging.DEBUG)


def generate_id():
    # Generate a random string of 5 characters
    random_string = ''.join(choices(string.ascii_letters + string.digits, k=5))
    # Prefix the random string with "iemap"
    return "iemap" + random_string


class MyDataModel(BaseModel):
    user_email: EmailStr
    institution: str
    id: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=datetime.now)

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = generate_id()
    # Add other fields as needed


# Pydantic model for JSON validation to handle the JSON payload in multi-part form data
class Checker:
    def __init__(self, model: Type[BaseModel]):
        self.model = model

    def __call__(self, data: str = Form(...)):
        try:
            return self.model.model_validate_json(data)
        except ValidationError as e:
            raise HTTPException(
                detail=jsonable_encoder(e.errors()),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


app = FastAPI()


@app.post("/test")
async def test_data(data: MyDataModel):
    return {"message": f"Data submitted {data}"}


# Define the main route, which returns the Uvicorn version and the current time
@app.get("/")
def main():
    return {"Uvicorn version: ": uvicorn.__version__, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# Define the route to upload data and a file
# The route expects a JSON payload and a file in the multi-part form data
# The logic is the following:
# 1. Validate the JSON payload using the Pydantic model
# 2. This model generate a random ID if it is not provided (as well as the current date)
# 3. Use async tasks to insert the data into MongoDB and save the file asynchronously
# 4. If any of the tasks fails, handle the exceptions and return an error message
# 5. If both tasks succeed, update the MongoDB document to add the filename to an array field in the document
# 6. Return a success message if everything is successful
# 7. If inserting the data into MongoDB succeeds but saving the file fails, add a message to the response indicating
#    that the data was saved successfully but the file was not saved
# 8. If updating the MongoDB document fails, raise an exception that
#    is caught and handled by deleting the uploaded file (if it exists) and returning an error message
@app.post("/upload")
async def upload_data_and_file(data: MyDataModel = Depends(Checker(MyDataModel)),
                               excel_file: UploadFile = File(...)):
    logger.info({"JSON Payload": data, "File": excel_file.filename})

    folder_where_file_will_be_saved = Path("uploaded_data")
    file_extension = Path(excel_file.filename).suffix
    file_name = f"{data.id}{file_extension}"
    file_path = folder_where_file_will_be_saved / file_name

    # define the MongoDB client, database and collection
    client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=3000)
    db = client["test_db"]
    collection = db["iemap_data"]
    result_insert = None
    try:

        # Check if the database connection is alive, and if not, raise an exception after 3 seconds
        await client.admin.command('ping')

        # Define two asynchronous functions to insert data into MongoDB and save the file
        async def insert_data():
            result = await collection.insert_one(data.dict())
            if result.inserted_id is None:
                raise Exception("Unable to insert data.")
            return result.inserted_id

        async def save_file():
            if file_path.exists() and file_path.is_file():
                # Raise an exception if the file already exists
                raise FileExistsError(f"The file {file_path} already exists.")
            async with aio_open(file_path, "wb") as f:
                await f.write(await excel_file.read())

        # result_insert, _ = await asyncio.gather(insert_data(), save_file())

        # create tasks for insert_data and save_file functions
        insert_data_task = asyncio.create_task(insert_data())
        save_file_task = asyncio.create_task(save_file())

        # wait for both tasks to complete (!! important to use asyncio.ALL_COMPLETED )
        done, pending = await asyncio.wait([insert_data_task, save_file_task], return_when=asyncio.ALL_COMPLETED)
        for task in done:
            if task == insert_data_task:
                # get the result of the insert_data_task and store it in result_insert (if no exception),
                # this is the ObjectId of the inserted document
                result_insert = task.result()
            elif task == save_file_task:
                # if save_file_task raises an exception, store it in save_file_exception and re-raise it
                save_file_exception = task.exception()
                if save_file_exception:
                    raise save_file_exception

        # If save_file_task succeeds, update the MongoDB document
        if save_file_task in done and not save_file_task.exception():
            # Update MongoDB document to add an array field containing the full filename
            result_update = await collection.update_one(
                {"_id": result_insert},
                {"$push": {"files": file_name}},
                upsert=True
            )
            is_doc_updated_successfully: bool = (result_update.modified_count == 1)
            if not is_doc_updated_successfully:
                raise Exception("Document not updated successfully")
            return {"message": "Data and file saved successfully!"}

    except PyMongoError as e:
        return {"message": "Unable to add data into MongoDB", "error": str(e)}
    except PermissionError as e:
        message = f"An error occurred while saving the Excel file"
        if result_insert is not None:
            message = f"Data saved successfully in MongoDB, but {message.lower()}"
        return {"message": message, "error": str(e)}
    except Exception as e:
        # Handle exceptions (e.g., database or file saving failure)
        if file_path.exists() and file_path.is_file():
            file_path.unlink()  # Remove the uploaded Excel file
        return {"message": "Unexpected error occurred", "error": str(e)}


# Define a route to download a file by its filename
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path("uploaded_data") / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), filename=filename)


# @app.exception_handler(ValidationError)
# async def validation_error_handler(request, exc):
#     good_objects = []
#     bad_objects = []
#     errors = {}
#
#     # Iterate over the list of objects
#     for index, obj in enumerate(exc.raw_value):
#         try:
#             # Validate the object using pydantic
#             validated_obj = MyDataModel(**obj)
#             good_objects.append(validated_obj)
#         except ValidationError as e:
#             # If validation error, add the object to bad objects
#             # and the error message to errors dictionary
#             bad_objects.append(obj)
#             errors[index] = e.messages

# Error handler for RequestValidationError, resulting from Pydantic validation errors in requests
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the exception to the console
    logger.error(f"An error occurred while validating data: {exc}")
    # Iterate through the errors and create a list of error messages
    error_messages = []
    for error in exc.errors():
        error_messages.append(f"Error at {'.'.join(map(str, error['loc']))}: {error['msg']}")

    # Join the error messages into a single string
    error_summary = "\n".join(error_messages)

    # Return a response
    return JSONResponse(
        status_code=442,
        content=jsonable_encoder({"detail": error_summary, "body": exc.errors()}),
    )

# https://stackoverflow.com/questions/77602055/how-to-upload-both-files-and-a-list-of-dictionaries-using-pydantics-basemodel-i

# check the link below for more details
# https://stackoverflow.com/questions/65504438/how-to-add-both-file-and-json-body-in-a-fastapi-post-request/70640522#70640522


# https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions
