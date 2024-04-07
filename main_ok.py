from fastapi import FastAPI, status, Form, UploadFile, File, Depends, Request
from pydantic import BaseModel, ValidationError, EmailStr
from fastapi.exceptions import HTTPException
from fastapi.encoders import jsonable_encoder
from typing import Optional, List
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class User(BaseModel):
    user_email: EmailStr
    institution: Optional[str] = None
    is_accepted: Optional[bool] = False


def checker(data: str = Form(...)):
    try:
        return User.model_validate_json(data)
    except ValidationError as e:
        raise HTTPException(
            detail=jsonable_encoder(e.errors()),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@app.post("/upload")
def submit(u: User = Depends(checker), excel_file: UploadFile = File(...)):  #files: List[UploadFile] = File(...)):
    return {"JSON Payload": u, "File": excel_file.filename}
    # return {"JSON Payload": u, "Filenames": [file.filename for file in files]}


@app.get("/", response_class=HTMLResponse)
def main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# https://stackoverflow.com/questions/65504438/how-to-add-both-file-and-json-body-in-a-fastapi-post-request/70640522#70640522