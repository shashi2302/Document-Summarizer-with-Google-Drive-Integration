"""
Setup Verification Script
Run this to verify your configuration before starting the main application
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename, description):
    """Check if a required file exists"""
    if Path(filename).exists():
        print(f"✅ {description} found: {filename}")
        return True
    else:
        print(f"❌ {description} NOT found: {filename}")
        return False

def check_env_variable(var_name):
    """Check if environment variable is set"""
    value = os.getenv(var_name)
    if value and value != f"your-{var_name.lower().replace('_', '-')}-here":
        print(f"✅ {var_name} is set")
        return True
    else:
        print(f"❌ {var_name} is NOT set or uses placeholder value")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'google.auth',
        'googleapiclient',
        'openai',
        'PyPDF2',
        'docx',
    ]
    
    print("\n📦 Checking Python Dependencies:")
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            all_installed = False
    
    return all_installed

def main():
    """Main verification function"""
    print("🔍 Document Summarizer - Setup Verification\n")
    print("=" * 60)
    
    # Check files
    print("\n📁 Checking Required Files:")
    files_ok = True
    files_ok &= check_file_exists("app.py", "Main application file")
    files_ok &= check_file_exists("requirements.txt", "Requirements file")
    files_ok &= check_file_exists("credentials.json", "Google OAuth credentials")
    
    # Check environment variables
    print("\n🔐 Checking Environment Variables:")
    
    # Try loading .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed (optional)")
    
    env_ok = True
    env_ok &= check_env_variable("OPENAI_API_KEY")
    env_ok &= check_env_variable("GOOGLE_DRIVE_FOLDER_ID")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Summary
    print("\n" + "=" * 60)
    print("\n📊 VERIFICATION SUMMARY:")
    
    if files_ok and env_ok and deps_ok:
        print("\n✅ All checks passed! You're ready to run the application.")
        print("\n🚀 Start the application with:")
        print("   python app.py")
        print("   or")
        print("   uvicorn app:app --reload")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\n📝 Setup instructions:")
        
        if not files_ok:
            print("\n  Files:")
            print("  - Ensure all project files are present")
            print("  - Download credentials.json from Google Cloud Console")
        
        if not env_ok:
            print("\n  Environment Variables:")
            print("  - Create a .env file with your API keys")
            print("  - Or set them as system environment variables")
            print("  - Copy .env.example to .env and fill in your values")
        
        if not deps_ok:
            print("\n  Dependencies:")
            print("  - Run: pip install -r requirements.txt")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()