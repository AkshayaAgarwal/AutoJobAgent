#!/usr/bin/env python3
"""
Gmail API Automation - Send emails automatically with Gmail API
Integrates with Ollama-generated emails to send via Gmail
"""

import os
import sys
import base64
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
from datetime import datetime

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_FILE = 'gmail_token.pickle'
CREDENTIALS_FILE = 'gmail_credentials.json'

def setup_gmail_credentials():
    """Setup Gmail API credentials (first time only)"""
    print(f"\n{'='*80}")
    print("GMAIL API SETUP")
    print(f"{'='*80}\n")
    
    print("📝 To enable Gmail automation, you need to set up Gmail API credentials.")
    print("\nFollow these steps:\n")
    
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project (name it 'Job Application Automation')")
    print("3. Enable Gmail API:")
    print("   - Search for 'Gmail API'")
    print("   - Click 'Enable'")
    print("4. Create OAuth 2.0 credentials:")
    print("   - Go to 'Credentials' → 'Create Credentials'")
    print("   - Choose 'OAuth client ID'")
    print("   - Select 'Desktop application'")
    print("   - Click 'Create'")
    print("5. Download the JSON file and save as 'gmail_credentials.json'")
    print("   (Place it in the same directory as this script)")
    print("\n6. On first run, it will open your browser to authorize")
    print("   - Click 'Allow' to grant permissions")
    print("   - This creates 'gmail_token.pickle' for future use")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ {CREDENTIALS_FILE} not found!")
        print("Please download it from Google Cloud Console and place it here.")
        return False
    
    return True

def authenticate_gmail():
    """Authenticate with Gmail API"""
    creds = None
    
    # Check if token already exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_gmail_service(creds):
    """Get Gmail API service"""
    return googleapiclient.discovery.build('gmail', 'v1', credentials=creds)

def send_email(service, to_email, subject, body, attachment_path=None, sender_email=None):
    """Send email via Gmail API"""
    
    # Create message
    message = MIMEMultipart()
    message['to'] = to_email
    message['from'] = sender_email if sender_email else 'me'
    message['subject'] = subject
    
    # Add body
    message.attach(MIMEText(body, 'plain'))
    
    # Add attachment if provided
    if attachment_path and os.path.exists(attachment_path):
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                message.attach(part)
        except Exception as e:
            print(f"   ⚠️  Could not attach file: {str(e)}")
    
    # Encode and send
    try:
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = {'raw': raw_message}
        
        result = service.users().messages().send(userId='me', body=send_message).execute()
        return True, result['id']
    except Exception as e:
        return False, str(e)

def read_email_from_file(email_file):
    """Read email from generated email file"""
    try:
        with open(email_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        to_email = ""
        subject = ""
        body_start = 0
        
        for idx, line in enumerate(lines):
            if line.startswith('TO:'):
                to_email = line.replace('TO:', '').strip()
            elif line.startswith('SUBJECT:'):
                subject = line.replace('SUBJECT:', '').strip()
            elif line.startswith('=' * 20):
                body_start = idx + 1
                break
        
        body = '\n'.join(lines[body_start:]).strip()
        
        return {
            'to': to_email,
            'subject': subject,
            'body': body
        }
    except Exception as e:
        print(f"Error reading email file: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python gmail_automation.py <email_directory_or_file> [resume_file_for_attachment]")
        print("\nExample 1 (send all in folder):")
        print("  python gmail_automation.py ollama_generated_emails/ my_resume.pdf")
        print("\nExample 2 (send single email):")
        print("  python gmail_automation.py ollama_generated_emails/93807043_Company.txt my_resume.pdf")
        sys.exit(1)
    
    email_input = sys.argv[1]
    resume_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n{'='*80}")
    print("GMAIL API AUTOMATED SENDER")
    print(f"{'='*80}\n")
    
    # Setup and authenticate
    print("🔐 Setting up Gmail API authentication...\n")
    
    if not setup_gmail_credentials():
        sys.exit(1)
    
    print("\n🔑 Authenticating with Gmail...")
    try:
        creds = authenticate_gmail()
        service = get_gmail_service(creds)
        print("✅ Gmail authentication successful!\n")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        print("\nMake sure:")
        print("  1. gmail_credentials.json exists in this directory")
        print("  2. You granted permissions in the browser popup")
        sys.exit(1)
    
    # Collect emails to send
    emails_to_send = []
    
    if os.path.isdir(email_input):
        # Send all emails in directory
        print(f"📁 Reading emails from directory: {email_input}\n")
        for filename in os.listdir(email_input):
            if filename.endswith('.txt'):
                filepath = os.path.join(email_input, filename)
                email_data = read_email_from_file(filepath)
                if email_data and email_data.get('to'):
                    emails_to_send.append({
                        'file': filename,
                        'data': email_data,
                        'path': filepath
                    })
    
    elif os.path.isfile(email_input):
        # Send single email
        print(f"📧 Reading email from file: {email_input}\n")
        email_data = read_email_from_file(email_input)
        if email_data and email_data.get('to'):
            emails_to_send.append({
                'file': os.path.basename(email_input),
                'data': email_data,
                'path': email_input
            })
    else:
        print(f"❌ File or directory not found: {email_input}")
        sys.exit(1)
    
    if not emails_to_send:
        print("❌ No emails found to send")
        sys.exit(1)
    
    print(f"✓ Found {len(emails_to_send)} email(s) to send\n")
    
    # Send emails
    print(f"{'='*80}")
    print(f"SENDING {len(emails_to_send)} EMAIL(S)")
    print(f"{'='*80}\n")
    
    sent_count = 0
    failed_count = 0
    
    for idx, email_item in enumerate(emails_to_send, 1):
        email_data = email_item['data']
        filename = email_item['file']
        
        to_email = email_data.get('to', '')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        if not to_email or '@' not in to_email:
            print(f"[{idx}/{len(emails_to_send)}] ⚠️  Invalid email: {filename}")
            print(f"   Recipient: {to_email}")
            failed_count += 1
            continue
        
        print(f"[{idx}/{len(emails_to_send)}] Sending to {to_email}")
        print(f"   Subject: {subject[:60]}...")
        
        # Send email
        success, result = send_email(
            service,
            to_email,
            subject,
            body,
            attachment_path=resume_file,
            sender_email=None
        )
        
        if success:
            print(f"   ✅ Sent successfully (ID: {result[:20]}...)\n")
            sent_count += 1
        else:
            print(f"   ❌ Failed: {result}\n")
            failed_count += 1
    
    # Summary
    print(f"\n{'='*80}")
    print("SEND SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successfully sent: {sent_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Success rate: {(sent_count/len(emails_to_send)*100):.1f}%\n")
    
    if sent_count > 0:
        print("📧 Emails have been sent!")
        print("🔍 Check your Gmail 'Sent' folder to verify")
        print("📋 Update your tracking spreadsheet with send dates")
        print("⏰ Follow up after 5 business days if no response\n")

if __name__ == "__main__":
    main()
