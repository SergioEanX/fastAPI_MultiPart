# FASTAPI Multi-Part example app
Example app to demonstrate how to upload files using FastAPI.   
It uses the `File` and `UploadFile` classes from the `fastapi` module.   
And a pydantic model to validate the request form data.


## Defined endpoints
- `/upload/` - POST method to upload a file
- `/download/{file_name}` - GET method to download a file
- `/` - GET method to simply return a message with Uvicorn version and the current time

## Notes
- The uploaded files are stored in the `uploaded_data/` directory
- To upload data and file, use axios or fetch API in from a NodeJS app as below:
```javascript
import axios from  'axios';
import fs from 'fs';
import FormData from 'form-data';
import readline from 'readline';

// JSON data to send along with the file
const jsonData = {
    user_email: 'valid.mail@mail.it', // use a valid email
    institution: 'ENEA',
    // Add other properties as needed
};

// Replace with your API endpoint for file uploads
const UPLOAD_URL = 'http://127.0.0.1:8000/upload';

// Path to the file you want to upload
const filePath = './files_to_upload/excel_file.xlsx'; // Update this

async function uploadFileAndData() {
    try {
        const formData = new FormData();

        formData.append("data",JSON.stringify(jsonData));
        formData.append('excel_file', fs.createReadStream(filePath));

        const response = await axios.post(UPLOAD_URL,
            formData,
            {
                headers:
                    {
                        'Content-Type': 'multipart/form-data',
                    },
            }
        );

        console.log('\nFile upload successful!');
        console.log('\nResponse:', response.data);
    } catch (error) {
        console.error('\nError uploading file:', error.message);
    }
}

// Create readline interface
const rl = readline.createInterface({
    prompt: 'Press any key to exit...\n',
    input: process.stdin,
    output: process.stdout
});

// Keep app running and exit it if any key is pressed
rl.on('line', () => {
    console.log('Exiting...');
    rl.close();
});

uploadFileAndData().catch((error) => {});

  ```