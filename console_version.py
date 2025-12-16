"""
Document Summarizer - Console Version
A command-line interface for the document summarizer
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import openai
import os
import io
import pickle
import PyPDF2
import docx
import csv
from datetime import datetime
from typing import List, Dict

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'YOUR_FOLDER_ID_HERE')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-api-key')
openai.api_key = OPENAI_API_KEY


def get_google_drive_service():
    """Authenticate with Google Drive"""
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)


def list_files_in_folder(service, folder_id: str) -> List[Dict]:
    """List supported documents in Google Drive folder"""
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        supported_files = [f for f in files if f['name'].lower().endswith(('.pdf', '.docx', '.txt'))]
        return supported_files
    
    except Exception as e:
        print(f"❌ Error listing files: {str(e)}")
        return []


def download_file(service, file_id: str, file_name: str) -> bytes:
    """Download file from Google Drive"""
    try:
        request = service.files().get_media(fileId=file_id)
        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   Download: {int(status.progress() * 100)}%", end='\r')
        
        print()  # New line after download
        return file_data.getvalue()
    
    except Exception as e:
        print(f"❌ Error downloading {file_name}: {str(e)}")
        return None


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting PDF: {str(e)}")
        return ""


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX"""
    try:
        docx_file = io.BytesIO(file_content)
        doc = docx.Document(docx_file)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting DOCX: {str(e)}")
        return ""


def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT"""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        print(f"❌ Error extracting TXT: {str(e)}")
        return ""


def extract_text(file_content: bytes, file_name: str) -> str:
    """Extract text based on file extension"""
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
    """Generate summary using OpenAI"""
    try:
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries. Provide summaries in 5-10 sentences."
                },
                {
                    "role": "user",
                    "content": f"Summarize this document titled '{file_name}':\n\n{text}"
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"❌ Error generating summary: {str(e)}"


def save_to_csv(summaries: List[Dict], filename: str):
    """Save summaries to CSV file"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['File Name', 'Summary', 'Web Link', 'Processed At']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for summary in summaries:
            writer.writerow({
                'File Name': summary['file_name'],
                'Summary': summary['summary'],
                'Web Link': summary.get('web_link', 'N/A'),
                'Processed At': summary['processed_at']
            })
    
    print(f"\n✅ CSV report saved: {filename}")


def print_summary(summary: Dict, index: int):
    """Print a single summary with formatting"""
    print("\n" + "=" * 80)
    print(f"📄 Document #{index}")
    print("=" * 80)
    print(f"\n📌 File Name: {summary['file_name']}")
    print(f"🔗 Link: {summary.get('web_link', 'N/A')}")
    print(f"⏰ Processed: {summary['processed_at']}")
    print(f"\n📝 Summary:\n{summary['summary']}")


def main():
    """Main console application"""
    print("=" * 80)
    print("📄 DOCUMENT SUMMARIZER - Console Version")
    print("=" * 80)
    
    try:
        # Authenticate with Google Drive
        print("\n🔐 Authenticating with Google Drive...")
        service = get_google_drive_service()
        print("✅ Authentication successful!")
        
        # List files
        print(f"\n📂 Scanning folder: {FOLDER_ID}")
        files = list_files_in_folder(service, FOLDER_ID)
        
        if not files:
            print("❌ No supported documents found in the folder.")
            return
        
        print(f"✅ Found {len(files)} documents to process")
        print("\nDocuments:")
        for i, file in enumerate(files, 1):
            print(f"  {i}. {file['name']}")
        
        # Process files
        summaries = []
        print("\n" + "=" * 80)
        print("🤖 Processing documents...")
        print("=" * 80)
        
        for i, file in enumerate(files, 1):
            file_id = file['id']
            file_name = file['name']
            web_link = file.get('webViewLink', '')
            
            print(f"\n[{i}/{len(files)}] Processing: {file_name}")
            
            # Download
            print("   Downloading...", end=' ')
            file_content = download_file(service, file_id, file_name)
            if not file_content:
                print("   ⚠️  Skipped (download failed)")
                continue
            print("✅")
            
            # Extract text
            print("   Extracting text...", end=' ')
            text = extract_text(file_content, file_name)
            if not text:
                print("❌ Failed")
                continue
            print(f"✅ ({len(text)} characters)")
            
            # Generate summary
            print("   Generating summary...", end=' ')
            summary = summarize_text(text, file_name)
            print("✅")
            
            # Store result
            summaries.append({
                'file_name': file_name,
                'summary': summary,
                'web_link': web_link,
                'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Display results
        print("\n" + "=" * 80)
        print("📊 RESULTS")
        print("=" * 80)
        print(f"\n✅ Successfully processed {len(summaries)} out of {len(files)} documents")
        
        for i, summary in enumerate(summaries, 1):
            print_summary(summary, i)
        
        # Save to CSV
        if summaries:
            csv_filename = f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            save_to_csv(summaries, csv_filename)
        
        print("\n" + "=" * 80)
        print("✨ Process complete!")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()