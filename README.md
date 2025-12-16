# Document-Summarizer-with-Google-Drive-Integration
A FastAPI application that connects to Google Drive, retrieves documents (PDF, DOCX, TXT), and generates AI-powered summaries using OpenAI GPT.

## Features

- **Google Drive OAuth2 Integration**: Secure authentication with Google Drive
- **Multi-format Support**: Handles PDF, DOCX, and TXT files
- **AI-Powered Summaries**: Uses OpenAI GPT-3.5 to generate concise summaries
- **Web Interface**: Clean, responsive HTML interface
- **CSV Export**: Download summaries as CSV reports
- **RESTful API**: JSON endpoints for programmatic access

## Requirements

- Python 3.8 or higher
- Google Cloud Platform account
- OpenAI API account
- Google Drive folder with documents

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd document-summarizer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Google Drive API

#### a. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### b. Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop app" as the application type
4. Download the credentials JSON file
5. Rename it to `credentials.json` and place it in the project root directory

### 4. Set Up OpenAI API

1. Sign up at [OpenAI](https://platform.openai.com/)
2. Generate an API key from your dashboard
3. Copy your API key

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
```

#### How to Get Google Drive Folder ID:

1. Open Google Drive in your browser
2. Navigate to the folder you want to use
3. The URL will look like: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. Copy the `FOLDER_ID_HERE` part

**Alternative**: You can also modify `app.py` directly and hardcode the values:

```python
FOLDER_ID = 'your-folder-id-here'
OPENAI_API_KEY = 'your-openai-key-here'
```

### 6. Run the Application

```bash
python app.py
```

Or using uvicorn directly:

```bash
uvicorn app:app --reload
```

The application will start at: `http://localhost:8000`

### 7. First Time Authentication

On first run:
1. A browser window will open asking you to sign in to Google
2. Grant the necessary permissions
3. The app will save a `token.pickle` file for future use

## Usage

### Web Interface

1. **Home Page** (`/`): Overview and navigation
2. **Process Documents** (`/process`): Fetches and summarizes all documents
3. **View Summaries** (`/view-summaries`): Displays results in a styled table
4. **Download CSV** (`/download-csv`): Exports summaries to CSV

### API Endpoints

#### Get All Summaries (JSON)
```bash
GET /api/summaries
```

Response:
```json
{
  "summaries": [
    {
      "file_name": "document.pdf",
      "summary": "This document discusses...",
      "web_link": "https://drive.google.com/...",
      "processed_at": "2024-12-15 14:30:00"
    }
  ],
  "count": 1
}
```

#### Process Documents
```bash
GET /process
```

## Project Structure

```
document-summarizer/
│
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── credentials.json       # Google OAuth credentials (you create this)
├── token.pickle          # OAuth token (auto-generated)
├── .env                  # Environment variables (you create this)
├── README.md             # This file
└── summaries_*.csv       # Generated CSV reports
```

## Security Notes

- Never commit `credentials.json`, `token.pickle`, or `.env` to version control
- Add these to your `.gitignore`:

```gitignore
credentials.json
token.pickle
.env
*.csv
__pycache__/
*.pyc
```

## Troubleshooting

### Issue: "credentials.json not found"
**Solution**: Download OAuth credentials from Google Cloud Console

### Issue: "Invalid folder ID"
**Solution**: Double-check your Google Drive folder ID from the URL

### Issue: "OpenAI API key invalid"
**Solution**: Verify your API key at platform.openai.com

### Issue: "Failed to extract text from PDF"
**Solution**: The PDF might be scanned/image-based. Consider adding OCR (pytesseract)

### Issue: "Rate limit exceeded"
**Solution**: OpenAI has rate limits. Add delays between API calls or upgrade your plan

### Key Components:

1. **Google Drive Authentication**: Uses OAuth2 flow with token caching
2. **File Processing**: Downloads files and extracts text based on type
3. **Text Extraction**:
   - PDF: PyPDF2
   - DOCX: python-docx
   - TXT: Direct decoding
4. **Summarization**: OpenAI GPT-3.5-turbo with system prompts
5. **Web Interface**: FastAPI with HTML templates
6. **Export**: CSV generation with timestamps
