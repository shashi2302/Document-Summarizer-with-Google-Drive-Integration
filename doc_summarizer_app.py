"""
Document Summarizer with Google Drive Integration
FastAPI application that summarizes documents from Google Drive
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import openai
import os
import io
import pickle
from pathlib import Path
import PyPDF2
import docx
import csv
from datetime import datetime
from typing import List, Dict
import json

app = FastAPI(title="Document Summarizer")

# Google Drive API Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Configuration
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'YOUR_FOLDER_ID_HERE')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-api-key')
openai.api_key = OPENAI_API_KEY

# Store summaries in memory (in production, use a database)
summaries_cache = []


def get_google_drive_service():
    """
    Authenticate with Google Drive using OAuth2
    Returns an authenticated Google Drive service object
    """
    creds = None
    
    # Token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.json should be downloaded from Google Cloud Console
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)


def list_files_in_folder(service, folder_id: str) -> List[Dict]:
    """
    List all documents in a specific Google Drive folder
    Supports .pdf, .docx, and .txt files
    """
    try:
        # Query to get files from specific folder
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        # Filter for supported file types
        supported_files = []
        for file in files:
            name = file['name'].lower()
            if name.endswith(('.pdf', '.docx', '.txt')):
                supported_files.append(file)
        
        return supported_files
    
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return []


def download_file(service, file_id: str, file_name: str) -> bytes:
    """
    Download a file from Google Drive
    Returns file content as bytes
    """
    try:
        request = service.files().get_media(fileId=file_id)
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        return file_data.getvalue()
    
    except Exception as e:
        print(f"Error downloading file {file_name}: {str(e)}")
        return None


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF file using PyPDF2
    """
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    
    except Exception as e:
        print(f"Error extracting PDF text: {str(e)}")
        return ""


def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extract text from DOCX file using python-docx
    """
    try:
        docx_file = io.BytesIO(file_content)
        doc = docx.Document(docx_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    except Exception as e:
        print(f"Error extracting DOCX text: {str(e)}")
        return ""


def extract_text_from_txt(file_content: bytes) -> str:
    """
    Extract text from TXT file
    """
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        print(f"Error extracting TXT text: {str(e)}")
        return ""


def extract_text(file_content: bytes, file_name: str) -> str:
    """
    Extract text from document based on file extension
    """
    file_name_lower = file_name.lower()
    
    if file_name_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_content)
    elif file_name_lower.endswith('.docx'):
        return extract_text_from_docx(file_content)
    elif file_name_lower.endswith('.txt'):
        return extract_text_from_txt(file_content)
    else:
        return ""


def summarize_text(text: str, file_name: str) -> str:
    """
    Summarize text using OpenAI GPT
    Returns a 5-10 sentence summary
    """
    try:
        # Truncate text if too long (GPT has token limits)
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of documents. Provide summaries in 5-10 sentences."
                },
                {
                    "role": "user",
                    "content": f"Please summarize the following document titled '{file_name}':\n\n{text}"
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    
    except Exception as e:
        print(f"Error summarizing text: {str(e)}")
        return f"Error generating summary: {str(e)}"


@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Home page with instructions
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Summarizer</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
                margin: 10px 5px;
                font-weight: bold;
            }
            .button:hover {
                background-color: #45a049;
            }
            .info {
                background-color: #e7f3ff;
                padding: 15px;
                border-left: 4px solid #2196F3;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 Document Summarizer</h1>
            <p>This application connects to Google Drive, retrieves documents, and generates AI-powered summaries.</p>
            
            <div class="info">
                <strong>Supported formats:</strong> PDF, DOCX, TXT
            </div>
            
            <div>
                <a href="/process" class="button">Process Documents</a>
                <a href="/view-summaries" class="button">View Summaries</a>
                <a href="/download-csv" class="button">Download CSV Report</a>
            </div>
            
            <h2>Setup Instructions:</h2>
            <ol>
                <li>Configure Google Drive credentials (credentials.json)</li>
                <li>Set GOOGLE_DRIVE_FOLDER_ID environment variable</li>
                <li>Set OPENAI_API_KEY environment variable</li>
                <li>Click "Process Documents" to start</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/process")
async def process_documents():
    """
    Process all documents in the Google Drive folder
    Extract text and generate summaries
    """
    global summaries_cache
    summaries_cache = []
    
    try:
        # Get Google Drive service
        service = get_google_drive_service()
        
        # List files in folder
        files = list_files_in_folder(service, FOLDER_ID)
        
        if not files:
            return {"message": "No supported documents found in the folder"}
        
        # Process each file
        for file in files:
            file_id = file['id']
            file_name = file['name']
            web_link = file.get('webViewLink', '')
            
            print(f"Processing: {file_name}")
            
            # Download file
            file_content = download_file(service, file_id, file_name)
            if not file_content:
                continue
            
            # Extract text
            text = extract_text(file_content, file_name)
            if not text:
                print(f"Could not extract text from {file_name}")
                continue
            
            # Generate summary
            summary = summarize_text(text, file_name)
            
            # Store result
            summaries_cache.append({
                'file_name': file_name,
                'summary': summary,
                'web_link': web_link,
                'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "message": f"Successfully processed {len(summaries_cache)} documents",
            "summaries": summaries_cache
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/view-summaries", response_class=HTMLResponse)
async def view_summaries():
    """
    Display summaries in a styled HTML table
    """
    if not summaries_cache:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Summaries</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; }
                .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .button { background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; 
                          border-radius: 5px; display: inline-block; margin: 10px 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>No Summaries Available</h1>
                <p>Please process documents first.</p>
                <a href="/" class="button">Go Home</a>
                <a href="/process" class="button">Process Documents</a>
            </div>
        </body>
        </html>
        """
        return html_content
    
    # Build HTML table
    rows = ""
    for idx, summary in enumerate(summaries_cache, 1):
        link_html = f'<a href="{summary["web_link"]}" target="_blank">View File</a>' if summary['web_link'] else 'N/A'
        rows += f"""
        <tr>
            <td>{idx}</td>
            <td><strong>{summary['file_name']}</strong></td>
            <td>{summary['summary']}</td>
            <td>{link_html}</td>
            <td>{summary['processed_at']}</td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Summaries</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .button {{
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
                margin: 10px 5px;
            }}
            .button:hover {{
                background-color: #45a049;
            }}
            a {{
                color: #2196F3;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 Document Summaries</h1>
            <p>Total documents processed: <strong>{len(summaries_cache)}</strong></p>
            
            <div>
                <a href="/" class="button">Home</a>
                <a href="/process" class="button">Refresh Summaries</a>
                <a href="/download-csv" class="button">Download CSV</a>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>File Name</th>
                        <th>Summary</th>
                        <th>Link</th>
                        <th>Processed At</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    return html_content


@app.get("/download-csv")
async def download_csv():
    """
    Generate and download CSV report of summaries
    """
    if not summaries_cache:
        raise HTTPException(status_code=404, detail="No summaries available. Process documents first.")
    
    # Create CSV file
    csv_filename = f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['File Name', 'Summary', 'Web Link', 'Processed At']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for summary in summaries_cache:
            writer.writerow({
                'File Name': summary['file_name'],
                'Summary': summary['summary'],
                'Web Link': summary.get('web_link', 'N/A'),
                'Processed At': summary['processed_at']
            })
    
    return FileResponse(
        csv_filename,
        media_type='text/csv',
        filename=csv_filename
    )


@app.get("/api/summaries")
async def get_summaries_api():
    """
    API endpoint to get summaries as JSON
    """
    return {"summaries": summaries_cache, "count": len(summaries_cache)}


if __name__ == "__main__":
    import uvicorn
    print("Starting Document Summarizer Application...")
    print("Visit http://localhost:8000 to access the application")
    uvicorn.run(app, host="0.0.0.0", port=8000)