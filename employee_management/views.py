import logging
import pandas as pd
from typing import Dict
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpRequest, HttpResponse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# Configuration
load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    CHUNK_SIZE = 10000
    MAX_COLUMNS = 29
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    MAX_WORKERS = 5  # For parallel email processing

class FileHandler:
    @staticmethod
    def validate_file(file) -> tuple[bool, str]:
        """Validate uploaded file extension and size."""
        if not file:
            return False, "No file uploaded"
        
        extension = file.name.split('.')[-1].lower()
        if extension not in Config.ALLOWED_EXTENSIONS:
            return False, f"Invalid file type. Allowed types: {', '.join(Config.ALLOWED_EXTENSIONS)}"
        
        if file.size > Config.MAX_FILE_SIZE:
            return False, f"File size exceeds {Config.MAX_FILE_SIZE // (1024*1024)}MB limit"
            
        return True, ""

    @staticmethod
    def process_file(file_path: str) -> pd.DataFrame:
        """Process uploaded file and return DataFrame."""
        if file_path.endswith('.csv'):
            chunks = pd.read_csv(file_path, chunksize=Config.CHUNK_SIZE, encoding='utf-8')
            data = pd.concat(chunks, ignore_index=True)
        else:
            data = pd.read_excel(file_path)
        
        return data.iloc[:, :Config.MAX_COLUMNS].fillna("N/A")

class EmailService:
    def __init__(self):
        self.sender_email = Config.EMAIL_HOST_USER
        self.sender_password = Config.EMAIL_HOST_PASSWORD

    @staticmethod
    def format_email_body(employee_data: Dict) -> str:
        """Format employee details into email body."""
        return (
            f"Dear {employee_data.get('Name', 'Employee')},\n\n"
            f"We are pleased to share your updated transportation details:\n\n"
            f"🔹 Employee Code: {employee_data.get('Emp Code', 'N/A')}\n"
            f"🔹 Area: {employee_data.get('Area', 'N/A')}\n"
            f"🔹 Location: {employee_data.get('Location-Delhi', 'N/A')}\n"
            f"🔹 Pickup Time: {employee_data.get('Pickup Time', 'N/A')}\n"
            f"🔹 Contact Number: {employee_data.get('Contact No.', 'N/A')}\n"
            f"🔹 Process: {employee_data.get('Process', 'N/A')}\n\n"
            "Please ensure you are available at the designated pickup location on time. "
            "If you have any questions or need further assistance, feel free to reach out.\n\n"
            "Best regards,\n"
            "Your Admin Team"
        )

    """Send email using SMTP with error handling."""
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        if '@' not in to_email:
            logger.warning(f"Invalid email format: {to_email}")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

def handle_employee_form(request: HttpRequest) -> HttpResponse:
    """Handle file upload and process employee data."""
    if request.method != 'POST':
        return render(request, 'front/index.html', 
                     {'data_dict': request.session.get('data_dict')})

    try:
        uploaded_file = request.FILES.get('employee_file')
        is_valid, error_message = FileHandler.validate_file(uploaded_file)
        
        if not is_valid:
            messages.error(request, error_message)
            return redirect('handle_employee_form')

        fs = FileSystemStorage(location=settings.MEDIA_ROOT)
        file_path = fs.save(uploaded_file.name, uploaded_file)
        full_path = fs.path(file_path)

        try:
            data = FileHandler.process_file(full_path)
            if data.empty:
                raise ValueError("The uploaded file contains no data")

            data_dict = data.to_dict(orient='records')
            request.session['data_dict'] = data_dict
            messages.success(request, 'File uploaded and processed successfully!')

        finally:
            fs.delete(file_path)

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        messages.error(request, f"Error processing file: {str(e)}")

    return render(request, 'front/index.html', 
                 {'data_dict': request.session.get('data_dict')})

"""Send emails to employees using parallel processing."""
def send_employee_emails(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return redirect('handle_employee_form')

    data_dict = request.session.get('data_dict')
    if not data_dict:
        messages.error(request, 'No data found. Please upload a valid file first.')
        return redirect('handle_employee_form')

    email_service = EmailService()
    messages.info(request, 'Sending emails to employees...')

    # Process emails in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        send_email_partial = partial(
            lambda row: email_service.send_email(row.get('Email', ''), 
            'Updated Roster', 
            email_service.format_email_body(row)
            )
        )
        results = list(executor.map(send_email_partial, data_dict))

    success_count = sum(results)
    total_count = len(results)
    messages.success(
        request,
        f'Email sending completed. {success_count}/{total_count} emails sent successfully.'
    )

    return redirect('handle_employee_form')