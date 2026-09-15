#!/usr/bin/env python3
"""
Ollama Email Generator - Generate personalized emails using local LLM (Ollama)
Now with FULL resume integration: the complete resume content is injected into
every prompt so Ollama writes emails grounded in your actual experience.
"""

import requests
import json
import sys
import os
from openpyxl import load_workbook

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"  # Change to your installed model name

# ===== YOUR PERSONAL DETAILS - EDIT THESE =====
YOUR_NAME = "Akshaya Agarwal"
YOUR_PHONE = "+61 469 838 346"
YOUR_EMAIL = "akshaya.agarwal.au@gmail.com"
YOUR_LINKEDIN = "https://www.linkedin.com/in/akshaya-agarwal13"
# ============================================

# How many characters of raw resume text to inject into each prompt.
# ~2500 chars keeps the prompt focused while carrying real substance.
MAX_RESUME_CHARS = 2500


def check_ollama_connection():
    """Check if Ollama is running and the model exists"""
    try:
        response = requests.get(
            "http://127.0.0.1:11434/api/tags",
            timeout=5
        )

        if response.status_code != 200:
            print(f"Ollama returned status {response.status_code}")
            return False

        models = response.json().get("models", [])

        print("Installed models:")
        for model in models:
            print("  -", model["name"])

        if not any(m["name"] == OLLAMA_MODEL for m in models):
            print(f"\nModel '{OLLAMA_MODEL}' is not installed.")
            return False

        print("Ollama is running.")
        return True

    except requests.exceptions.ConnectionError:
        print("Cannot connect to Ollama.")
        print("Run: ollama serve")
        return False

    except Exception as e:
        print(e)
        return False


# ---------------------------------------------------------------------------
# RESUME LOADING
# ---------------------------------------------------------------------------

def extract_resume_text(resume_file):
    """
    Built-in fallback: extract raw text from the resume file directly.
    Supports .pdf, .docx and .txt. Used when resume_parser.py is missing
    or returns no usable text.
    """
    ext = os.path.splitext(resume_file)[1].lower()

    try:
        if ext == ".pdf":
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(resume_file) as pdf:
                    for page in pdf.pages:
                        text_parts.append(page.extract_text() or "")
                return "\n".join(text_parts).strip()
            except ImportError:
                from pypdf import PdfReader
                reader = PdfReader(resume_file)
                return "\n".join((p.extract_text() or "") for p in reader.pages).strip()

        elif ext == ".docx":
            from docx import Document
            doc = Document(resume_file)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()

        elif ext in (".txt", ".md"):
            with open(resume_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()

        else:
            print(f"⚠️  Unsupported resume format '{ext}'. Use PDF, DOCX or TXT.")
            return ""

    except ImportError as e:
        print(f"⚠️  Missing library to read {ext} files: {e}")
        print("   Install it with: pip install pdfplumber python-docx pypdf")
        return ""
    except Exception as e:
        print(f"⚠️  Could not extract resume text: {e}")
        return ""


def load_resume(resume_file):
    """
    Load resume data. Tries resume_parser.parse_resume first (if available),
    then ALWAYS ensures we have the full raw text — that raw text is what
    makes the generated emails specific instead of generic.
    """
    if not os.path.exists(resume_file):
        print(f"❌ Resume file not found: {resume_file}")
        return None

    resume_data = {}

    # 1) Try the external parser if it exists
    try:
        from resume_parser import parse_resume
        parsed = parse_resume(resume_file)
        if parsed:
            resume_data = parsed
            print("✓ resume_parser.py data loaded")
    except ImportError:
        print("ℹ️  resume_parser.py not found — using built-in resume reader")
    except Exception as e:
        print(f"⚠️  resume_parser failed ({e}) — falling back to built-in reader")

    # 2) Always get the raw text (parser output alone is usually too thin)
    raw_text = ""
    if isinstance(resume_data, dict):
        raw_text = resume_data.get("raw_text") or resume_data.get("text") or ""

    if not raw_text or len(raw_text) < 200:
        raw_text = extract_resume_text(resume_file)

    if not raw_text:
        print("❌ Could not read any text from your resume. Check the file.")
        return None

    if not isinstance(resume_data, dict):
        resume_data = {}
    resume_data["raw_text"] = raw_text

    print(f"✓ Resume loaded: {len(raw_text)} characters of text")
    return resume_data


def build_resume_context(resume_data):
    """
    Build a rich, structured RESUME block for the prompt from WHATEVER fields
    are available — no assumptions about resume_parser's exact key names.
    """
    lines = []

    def add(label, value):
        if not value:
            return
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value if v)
        value = str(value).strip()
        if value and value.lower() not in ("n/a", "none", "unknown"):
            lines.append(f"- {label}: {value}")

    # Common structured fields (present only if resume_parser provided them)
    add("Name", resume_data.get("name") or YOUR_NAME)
    add("Email", resume_data.get("email") or YOUR_EMAIL)
    add("Phone", resume_data.get("phone") or YOUR_PHONE)
    add("LinkedIn", resume_data.get("linkedin") or YOUR_LINKEDIN)
    add("Summary", resume_data.get("summary") or resume_data.get("professional_summary"))
    add("Years of Experience", resume_data.get("experience_years"))
    add("Current Role", resume_data.get("current_role") or resume_data.get("current_title"))
    add("Companies", resume_data.get("companies"))
    add("Technical Skills", resume_data.get("technical_stack") or resume_data.get("skills"))
    add("Education", resume_data.get("education"))
    add("Certifications", resume_data.get("certifications"))
    add("Key Projects", resume_data.get("projects"))
    add("Achievements", resume_data.get("achievements"))

    # The full raw resume text — the most important part.
    raw = resume_data.get("raw_text", "")
    if len(raw) > MAX_RESUME_CHARS:
        raw = raw[:MAX_RESUME_CHARS] + "\n[...resume truncated for brevity...]"

    context = ""
    if lines:
        context += "STRUCTURED PROFILE:\n" + "\n".join(lines) + "\n\n"
    context += "FULL RESUME TEXT (source of truth — use ONLY facts from here):\n" + raw

    return context


# ---------------------------------------------------------------------------
# EMAIL GENERATION
# ---------------------------------------------------------------------------

def generate_email_with_ollama(job_data, resume_data):
    """Generate personalized email using Ollama, grounded in the full resume"""

    job_title = job_data.get('job_title', 'the position')
    company = job_data.get('company_name', 'the company')
    tech_stack = str(job_data.get('tech_stack', ''))[:300]
    responsibilities = str(job_data.get('key_responsibilities', ''))[:300]
    requirements = str(job_data.get('essential_requirements', ''))[:300]
    company_focus = str(job_data.get('company_focus', ''))[:300]

    resume_context = build_resume_context(resume_data)

    # System message keeps small local models on-task
    system_prompt = (
        "You are a professional cover-letter writer. You write concise, specific, "
        "fact-based job application emails. You NEVER invent skills, employers, "
        "metrics or achievements that are not in the applicant's resume."
    )

    prompt = f"""Write a professional job application email using the job details and the applicant's resume below.

JOB DETAILS:
- Position: {job_title}
- Company: {company}
- Required Tech: {tech_stack}
- Key Responsibilities: {responsibilities}
- Requirements: {requirements}
- Company Focus: {company_focus}

APPLICANT'S RESUME:
{resume_context}

RULES:
1. Professional, formal tone.
2. Reference the specific role "{job_title}" at "{company}" in the opening line.
3. Pick 2-3 REAL skills/experiences from the resume that match this job's requirements and name them explicitly — do not list every skill.
4. Only claim experience, technologies and achievements that actually appear in the resume above. NEVER invent numbers, companies or projects.
5. Show one sentence of understanding of what the company does (based on Company Focus).
6. 3 short paragraphs, under 220 words total.
7. Start the body with "Hi Hiring Team," (or "Hi {company} Team,").
8. End EXACTLY with this closing block, with no placeholders:

Best regards,
{YOUR_NAME}
{YOUR_PHONE}
{YOUR_EMAIL}
{YOUR_LINKEDIN}

Output format (nothing else):
Subject: <one concise subject line mentioning the role>
Body:
<the email body including the closing block>

Generate ONLY the email now:"""

    print(f"🤖 Generating email with Ollama ({OLLAMA_MODEL})...")

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": prompt,
                "stream": False,
                # NOTE: Ollama only honours these inside "options"
                "options": {
                    "temperature": 0.5,   # lower = more factual, less rambling
                    "top_p": 0.9,
                    "num_predict": 700,   # cap output length
                    "repeat_penalty": 1.1
                }
            },
            timeout=180
        )

        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '')
            if generated_text.strip():
                print("✅ Email generated successfully")
                return generated_text
            print("⚠️  Ollama returned an empty response")
            return None
        else:
            print(f"❌ Ollama error: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print("⏱️  Ollama generation timed out. Try a smaller/faster model.")
        return None
    except Exception as e:
        print(f"❌ Error calling Ollama: {str(e)}")
        return None


def extract_subject_and_body(email_text):
    """Extract subject and body from generated email"""
    lines = email_text.split('\n')
    subject = ""
    body_lines = []

    in_body = False
    for line in lines:
        if line.strip().startswith('Subject:'):
            subject = line.split('Subject:', 1)[1].strip()
        elif line.strip() in ('Body:', 'Email:') or line.strip().startswith('Body:'):
            in_body = True
            # handle "Body: <text on same line>"
            after = line.split('Body:', 1)[-1].strip() if 'Body:' in line else ""
            if after:
                body_lines.append(after)
        elif in_body:
            body_lines.append(line)

    body = '\n'.join(body_lines).strip()

    # Fallback: model didn't follow the format — treat everything after the
    # subject line as the body
    if not body:
        remaining = [l for l in lines if not l.strip().startswith('Subject:')]
        body = '\n'.join(remaining).strip()

    # Replace any placeholder text with actual user details
    replacements = {
        '[Your Full Name]': YOUR_NAME,
        '[Your Name]': YOUR_NAME,
        '[Your Phone Number]': YOUR_PHONE,
        '[Your Phone]': YOUR_PHONE,
        '[Your Email Address]': YOUR_EMAIL,
        '[Your Email]': YOUR_EMAIL,
        '[Your LinkedIn Profile URL]': YOUR_LINKEDIN,
        '[Your LinkedIn]': YOUR_LINKEDIN,
    }
    for placeholder, actual in replacements.items():
        body = body.replace(placeholder, actual)
        subject = subject.replace(placeholder, actual)

    # Guarantee the sign-off block exists with real details
    if YOUR_PHONE not in body or YOUR_EMAIL not in body:
        body = body.rstrip()
        body += (
            f"\n\nBest regards,\n{YOUR_NAME}\n{YOUR_PHONE}\n"
            f"{YOUR_EMAIL}\n{YOUR_LINKEDIN}"
        )

    return subject.strip(), body


# ---------------------------------------------------------------------------
# JOB READING / SAVING (unchanged behaviour)
# ---------------------------------------------------------------------------

def read_jobs_from_xlsx(xlsx_file):
    """Read job data from cleaned XLSX - from both sheets"""
    jobs = []
    try:
        wb = load_workbook(xlsx_file)

        if "Job Opportunities" not in wb.sheetnames:
            print("ERROR: 'Job Opportunities' sheet not found in XLSX")
            return []

        ws_opportunities = wb["Job Opportunities"]

        headers_opp = {}
        for col_idx, cell in enumerate(ws_opportunities[1], 1):
            if cell.value:
                headers_opp[cell.value.lower()] = col_idx

        ws_details = None
        headers_details = {}
        if "Job Details" in wb.sheetnames:
            ws_details = wb["Job Details"]
            for col_idx, cell in enumerate(ws_details[1], 1):
                if cell.value:
                    headers_details[cell.value.lower()] = col_idx

        for row_idx in range(2, ws_opportunities.max_row + 1):
            job_data = {}

            for col_name, col_idx in headers_opp.items():
                value = ws_opportunities.cell(row=row_idx, column=col_idx).value
                job_data[col_name] = value if value else ""

            if ws_details:
                job_id = job_data.get('job id', '')
                for detail_row in range(2, ws_details.max_row + 1):
                    detail_job_id = ws_details.cell(row=detail_row, column=headers_details.get('job id', 1)).value
                    if str(detail_job_id) == str(job_id):
                        for col_name, col_idx in headers_details.items():
                            if col_name not in job_data or not job_data[col_name]:
                                value = ws_details.cell(row=detail_row, column=col_idx).value
                                job_data[col_name] = value if value else ""
                        break

            if 'job id' in job_data:
                job_data['job_id'] = job_data['job id']
            if 'job title' in job_data:
                job_data['job_title'] = job_data['job title']
            if 'company' in job_data:
                job_data['company_name'] = job_data['company']
            if 'contact email' in job_data:
                job_data['contact_email'] = job_data['contact email']

            if job_data.get('job_id') and job_data.get('job_title'):
                contact_email = job_data.get('contact_email', '')
                if not contact_email or contact_email == 'N/A' or contact_email == '':
                    print(f"  WARNING: Job {job_data.get('job_id')} has no contact email")

                jobs.append(job_data)

        return jobs
    except Exception as e:
        print(f"Error reading XLSX: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def save_generated_emails(emails_data, output_dir):
    """Save generated emails to files"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for email_info in emails_data:
        filename = f"{email_info['job_id']}_{email_info['company'].replace(' ', '_')[:20]}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"TO: {email_info['contact_email']}\n")
            f.write(f"SUBJECT: {email_info['subject']}\n")
            f.write("=" * 80 + "\n\n")
            f.write(email_info['body'])

        print(f"   ✅ Saved: {filename}")

    print(f"\n✓ All emails saved to: {output_dir}/")


def main():
    if len(sys.argv) < 3:
        print("Usage: python ollama_email_generator.py <jobs_cleaned.xlsx> <resume_file> [output_dir]")
        print("\nExample: python ollama_email_generator.py jobs_cleaned.xlsx my_resume.pdf generated_emails")
        sys.exit(1)

    xlsx_file = sys.argv[1]
    resume_file = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "ollama_generated_emails"

    print(f"\n{'='*80}")
    print("OLLAMA AUTOMATED EMAIL GENERATOR")
    print(f"{'='*80}\n")

    # 1. Check Ollama connection
    print("🔌 Checking Ollama connection...")
    if not check_ollama_connection():
        sys.exit(1)

    # 2. Load resume (parser + full raw text)
    print(f"\n📖 Loading your resume: {resume_file}")
    resume_data = load_resume(resume_file)
    if not resume_data:
        sys.exit(1)

    # Show a short preview so you can confirm the resume was read correctly
    preview = resume_data.get("raw_text", "")[:200].replace("\n", " ")
    print(f"   Preview: {preview}...")

    # 3. Read jobs from XLSX
    print(f"\n📋 Reading jobs from: {xlsx_file}")
    jobs = read_jobs_from_xlsx(xlsx_file)

    if not jobs:
        print("❌ No jobs found. Make sure you have the cleaned XLSX file.")
        sys.exit(1)

    print(f"✓ Found {len(jobs)} jobs")

    print("\n📧 Contact Emails Found:")
    has_emails = False
    for job in jobs[:5]:
        email = job.get('contact_email', 'N/A')
        if email and email != 'N/A':
            has_emails = True
        print(f"  - {job.get('job_id', 'N/A')}: {job.get('company_name', 'N/A')} → {email}")
    if len(jobs) > 5:
        print(f"  ... and {len(jobs) - 5} more")

    if not has_emails:
        print("\n⚠️  WARNING: No contact emails found! Check your XLSX file.")
    print()

    # 4. Generate emails
    print(f"{'='*80}")
    print(f"GENERATING {len(jobs)} PERSONALIZED EMAILS WITH OLLAMA")
    print(f"{'='*80}\n")

    generated_emails = []

    for idx, job in enumerate(jobs, 1):
        print(f"\n[{idx}/{len(jobs)}] {job.get('job_title', 'Job')} at {job.get('company_name', 'Company')}")

        email_text = generate_email_with_ollama(job, resume_data)

        if email_text:
            subject, body = extract_subject_and_body(email_text)

            email_data = {
                'job_id': job.get('job_id', 'unknown'),
                'job_title': job.get('job_title', 'N/A'),
                'company': job.get('company_name', 'N/A'),
                'contact_email': job.get('contact_email', 'N/A'),
                'subject': subject if subject else f"Application for {job.get('job_title', 'Position')} at {job.get('company_name', 'Company')}",
                'body': body if body else email_text
            }

            generated_emails.append(email_data)

            if subject:
                print(f"   📧 Subject: {subject[:60]}...")
            if body:
                print(f"   📝 Body: {body[:100]}...")
        else:
            print(f"   ⚠️  Failed to generate email")

    print(f"\n{'='*80}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*80}\n")

    if generated_emails:
        print(f"✅ Successfully generated {len(generated_emails)}/{len(jobs)} emails\n")

        print("💾 Saving emails to files...")
        save_generated_emails(generated_emails, output_dir)

        print(f"\n✅ All done! Generated emails are ready in: {output_dir}/")
        print(f"\n📧 Next step: Run gmail_automation.py to send these emails automatically!")
    else:
        print("❌ No emails were generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()