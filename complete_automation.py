#!/usr/bin/env python3
"""
COMPLETE AUTOMATION SYSTEM - Master Script
Runs: Resume Parse → Email Generation (Ollama) → Gmail Send (Fully Automated)
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: {description} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def main():
    print(f"\n{'='*80}")
    print("🚀 COMPLETE JOB APPLICATION AUTOMATION SYSTEM")
    print(f"{'='*80}\n")
    
    print("This system will:")
    print("  1. Parse your resume")
    print("  2. Read job data from XLSX")
    print("  3. Generate personalized emails using Ollama (Gwen 2.7)")
    print("  4. Send emails automatically via Gmail API")
    print("  5. Track everything in a spreadsheet\n")
    
    # Check required files
    print("📋 Checking required files...\n")
    
    required_files = {
        'jobs_cleaned.xlsx': 'Cleaned job database',
        'resume_parser.py': 'Resume parser script',
        'ollama_email_generator.py': 'Ollama email generator',
        'gmail_automation.py': 'Gmail automation script'
    }
    
    missing_files = []
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"  ✅ {filename} - {description}")
        else:
            print(f"  ❌ {filename} - {description} (MISSING)")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        print("Make sure all scripts are in the same directory")
        sys.exit(1)
    
    # Get user inputs
    print(f"\n{'='*80}")
    print("⚙️  CONFIGURATION")
    print(f"{'='*80}\n")
    
    # Resume file
    print("1️⃣  RESUME FILE")
    print("   Supported formats: .pdf, .docx, .txt")
    resume_file = input("   Enter path to your resume: ").strip()
    
    if not os.path.exists(resume_file):
        print(f"   ❌ Resume file not found: {resume_file}")
        sys.exit(1)
    print(f"   ✅ Resume: {resume_file}")
    
    # Check Ollama
    print("\n2️⃣  OLLAMA MODEL")
    print("   Using: Gwen 2.7")
    
    # Gmail setup
    print("\n3️⃣  GMAIL API")
    print("   Checking for credentials...")
    if not os.path.exists('gmail_credentials.json'):
        print("   ⚠️  gmail_credentials.json not found")
        print("   You'll be prompted to authorize on first send")
    else:
        print("   ✅ Gmail credentials found")
    
    # Ask for batch size
    print("\n4️⃣  BATCH SIZE")
    max_emails = input("   How many emails to generate? (default: all): ").strip()
    
    try:
        max_emails = int(max_emails) if max_emails else None
    except:
        max_emails = None
    
    # Ask for send confirmation
    print("\n5️⃣  AUTO-SEND")
    auto_send = input("   Automatically send emails after generation? (y/n): ").strip().lower() == 'y'
    
    # Ask for resume attachment
    print("\n6️⃣  RESUME ATTACHMENT")
    attach_resume = input("   Attach resume to each email? (y/n): ").strip().lower() == 'y'
    
    print(f"\n{'='*80}")
    print("✅ CONFIGURATION COMPLETE")
    print(f"{'='*80}\n")
    
    print(f"Summary:")
    print(f"  Resume: {resume_file}")
    print(f"  Jobs file: jobs_cleaned.xlsx")
    print(f"  Ollama model: gwen2.7")
    print(f"  Max emails: {max_emails if max_emails else 'All'}")
    print(f"  Auto-send: {'Yes' if auto_send else 'No'}")
    print(f"  Attach resume: {'Yes' if attach_resume else 'No'}\n")
    
    confirm = input("Start automation? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    print(f"\n{'='*80}")
    print("🚀 STARTING AUTOMATION")
    print(f"{'='*80}\n")
    
    # Step 1: Parse Resume
    print("STEP 1: Parse Resume")
    print("-" * 80)
    cmd = f"python resume_parser.py '{resume_file}'"
    if not run_command(cmd, "Parsing resume"):
        sys.exit(1)
    
    # Step 2: Generate Emails with Ollama
    print("\n\nSTEP 2: Generate Emails (Ollama)")
    print("-" * 80)
    output_dir = "ollama_generated_emails"
    cmd = f"python ollama_email_generator.py jobs_cleaned.xlsx '{resume_file}' {output_dir}"
    if not run_command(cmd, "Generating emails with Ollama"):
        sys.exit(1)
    
    # Step 3: Send Emails (if auto-send enabled)
    if auto_send:
        print("\n\nSTEP 3: Send Emails (Gmail API)")
        print("-" * 80)
        
        resume_arg = f"'{resume_file}'" if attach_resume else ""
        cmd = f"python gmail_automation.py {output_dir} {resume_arg}"
        
        confirm_send = input("\n⚠️  Ready to send emails. Continue? (y/n): ").strip().lower()
        if confirm_send == 'y':
            if not run_command(cmd, "Sending emails via Gmail"):
                sys.exit(1)
        else:
            print("Skipped automatic sending.")
            print(f"You can send later with: python gmail_automation.py {output_dir} {resume_arg}")
    else:
        print("\n\nSTEP 3: SKIPPED (Auto-send disabled)")
        print("-" * 80)
        print(f"Your generated emails are in: {output_dir}/")
        print(f"To send them manually, run:")
        if attach_resume:
            print(f"  python gmail_automation.py {output_dir} '{resume_file}'")
        else:
            print(f"  python gmail_automation.py {output_dir}")
    
    # Final summary
    print(f"\n\n{'='*80}")
    print("✅ AUTOMATION COMPLETE!")
    print(f"{'='*80}\n")
    
    print("📊 SUMMARY:")
    print(f"  Generated emails: {output_dir}/")
    
    if auto_send:
        print(f"  Status: Emails sent via Gmail!")
        print(f"\n📋 NEXT STEPS:")
        print(f"  1. Check your Gmail 'Sent' folder")
        print(f"  2. Update your tracking spreadsheet")
        print(f"  3. Monitor for responses (check daily)")
        print(f"  4. Follow up after 5 business days")
    else:
        print(f"  Status: Emails generated, ready to send")
        print(f"\n📋 NEXT STEPS:")
        print(f"  1. Review emails in {output_dir}/ folder")
        print(f"  2. Run gmail_automation.py to send")
        print(f"  3. Update tracking spreadsheet")
        print(f"  4. Monitor for responses")
    
    print(f"\n🎉 Your job applications are on their way!\n")

if __name__ == "__main__":
    main()
