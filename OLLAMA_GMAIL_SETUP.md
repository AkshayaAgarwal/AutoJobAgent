# 🚀 Complete Ollama + Gmail Automation Setup Guide

---

## 📌 **What You Have**

You now have a **fully automated job application system** that:

1. ✅ **Parses your resume** (PDF, DOCX, or TXT)
2. ✅ **Reads job data** from your cleaned XLSX
3. ✅ **Generates personalized emails** using Ollama locally (Gwen 2.7)
4. ✅ **Sends emails automatically** via Gmail API
5. ✅ **Tracks everything** in a spreadsheet

---

## 🔧 **Prerequisites**

### **Required Software:**
- Python 3.7+ (already installed)
- Ollama running locally with Gwen 2.7 model
- Gmail account with 2-factor authentication

### **Python Packages:**
```bash
pip install requests openpyxl google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Optional (for PDF resume parsing):
```bash
pip install pdfplumber python-docx
```

---

## 📋 **File Structure**

Your automation system consists of:

```
├── job_data_cleaner.py                 # Cleans Apify JSON
├── email_generator.py                  # Generates emails (old version)
├── resume_parser.py                    # Parses your resume
├── ollama_email_generator.py           # Generates emails with Ollama
├── gmail_automation.py                 # Sends via Gmail API
├── complete_automation.py              # Master script (runs everything)
├── jobs_cleaned.xlsx                   # Your job database
├── my_resume.pdf                       # Your resume (you provide)
└── gmail_credentials.json              # Gmail OAuth (you create)
```

---

## 🔑 **Step 1: Setup Gmail API (One-Time)**

### **1.1 Create Google Cloud Project**

1. Go to: https://console.cloud.google.com/
2. Click "Select a Project" → "New Project"
3. Name it: "Job Application Automation"
4. Click "Create"

### **1.2 Enable Gmail API**

1. In Google Cloud Console, search for "Gmail API"
2. Click on it
3. Click "Enable"
4. Wait a few seconds for it to enable

### **1.3 Create OAuth 2.0 Credentials**

1. Click "Create Credentials" (blue button)
2. Select: "OAuth client ID"
3. If prompted: Choose "Desktop application"
4. Click "Create"
5. Click "Download" (JSON file)
6. Save as `gmail_credentials.json` in your script directory

### **1.4 Setup Consent Screen (If Needed)**

If you get an error about consent screen:

1. Go to "OAuth consent screen" tab
2. Choose "External"
3. Click "Create"
4. Fill in:
   - App name: "Job Application Automation"
   - User support email: Your email
   - Developer contact: Your email
5. Click "Save and Continue"
6. Click "Add or Remove Scopes"
7. Search for "Gmail API" and add it
8. Save and continue through rest
9. Go back to credentials and create again

### **Result:**
You should have `gmail_credentials.json` file in your script directory.

---

## 🤖 **Step 2: Verify Ollama Setup**

### **2.1 Check Ollama is Running**

Open terminal and run:
```bash
ollama list
```

You should see:
```
NAME            ID              SIZE    MODIFIED
gwen2.7         xxxx            xxxGB   x days ago
```

### **2.2 If Gwen 2.7 is not installed:**

```bash
ollama pull gwen2.7
```

This will download the model (might take a while depending on your internet).

### **2.3 Start Ollama Server**

Make sure Ollama is running:
```bash
ollama serve
```

You should see:
```
Listening on 127.0.0.1:11434
```

Leave this terminal open while running the automation.

---

## 📄 **Step 3: Prepare Your Files**

### **3.1 Your Resume**

You need to provide your resume. Supported formats:
- **PDF** (recommended): `my_resume.pdf`
- **Word**: `my_resume.docx`
- **Text**: `my_resume.txt`

### **3.2 Job Database**

You should already have:
- `jobs_cleaned.xlsx` (from job_data_cleaner.py)

### **3.3 All Scripts**

Make sure these are in the same directory:
- `resume_parser.py`
- `ollama_email_generator.py`
- `gmail_automation.py`
- `complete_automation.py`
- `gmail_credentials.json` (you downloaded this)

---

## 🎯 **Step 4: Run the Complete Automation**

### **Quick Start (Recommended):**

```bash
python complete_automation.py
```

This will guide you through:
1. Selecting your resume file
2. Confirming settings
3. Generating emails with Ollama
4. Sending via Gmail

### **Advanced: Run Each Step Separately**

#### **Option A: Parse Resume Only**
```bash
python resume_parser.py my_resume.pdf
```

#### **Option B: Generate Emails Only**
```bash
python ollama_email_generator.py jobs_cleaned.xlsx my_resume.pdf generated_emails
```

#### **Option C: Send Generated Emails**
```bash
python gmail_automation.py generated_emails/ my_resume.pdf
```

---

## 📊 **Complete Workflow**

### **Full Automation (All in One):**

```bash
# Terminal 1: Start Ollama (leave running)
ollama serve

# Terminal 2: Run complete automation
python complete_automation.py
```

### **What Happens:**

1. **Resume Parsing**
   ```
   📄 Parsing resume: my_resume.pdf
   ✅ Resume Parsed Successfully!
      📧 Email: john@example.com
      📱 Phone: +61 400 123 456
      🔗 LinkedIn: linkedin.com/in/johnsmith
      💻 Tech Stack: Python, React, Node.js, ...
   ```

2. **Email Generation (Ollama)**
   ```
   🤖 Generating email with Ollama (gwen2.7)...
   ✅ Email generated successfully
   
   [1/50] Full Stack AI Engineer at EasyAsset
      📧 Subject: Full Stack Developer Application...
      📝 Body: Hi Hiring Team, I came across the...
   ```

3. **Email Sending (Gmail)**
   ```
   📧 [1/50] Sending to support@easyasset.com.au
      Subject: Full Stack Developer Application...
      ✅ Sent successfully (ID: xxxxxxx...)
   ```

4. **Summary**
   ```
   ✅ Successfully sent: 50
   ❌ Failed: 0
   📊 Success rate: 100%
   ```

---

## 🛠️ **Troubleshooting**

### **Issue 1: "Cannot connect to Ollama"**

**Error Message:**
```
❌ Cannot connect to Ollama. Make sure it's running on localhost:11434
```

**Solution:**
1. Open a new terminal
2. Run: `ollama serve`
3. Keep it running while using the automation

### **Issue 2: "Gmail credentials not found"**

**Error Message:**
```
❌ gmail_credentials.json not found!
```

**Solution:**
1. Download `gmail_credentials.json` from Google Cloud Console
2. Place it in the same directory as the scripts
3. See Step 1 above for detailed instructions

### **Issue 3: "Gmail authentication failed"**

**First time only - expected:**
```
🌐 Opening browser for Gmail authorization...
```

Just click "Allow" when prompted. This creates `gmail_token.pickle`.

### **Issue 4: "Gwen 2.7 model not found"**

**Error Message:**
```
Model gwen2.7 not found
```

**Solution:**
```bash
ollama pull gwen2.7
```

Wait for download to complete.

### **Issue 5: "Resume parser not working"**

**Solution:**
```bash
# For PDF support
pip install pdfplumber

# For Word support
pip install python-docx

# Then try again
python resume_parser.py my_resume.pdf
```

### **Issue 6: "No emails generated"**

**Reasons:**
1. XLSX file is not cleaned (use `job_data_cleaner.py` first)
2. Job data is missing required fields
3. Ollama generation failed (check Ollama is running)

**Solution:**
1. Check that `jobs_cleaned.xlsx` has data
2. Run test: `python resume_parser.py my_resume.pdf`
3. Check Ollama is running: `ollama serve`

---

## 📈 **Performance Tips**

### **Speed Up Email Generation:**

1. **Use faster model** (if available):
   ```bash
   ollama pull mistral  # Faster than Gwen 2.7
   # Then modify ollama_email_generator.py
   # Change: OLLAMA_MODEL = "mistral"
   ```

2. **Reduce email count** (process in batches):
   ```bash
   python complete_automation.py
   # When asked: "How many emails to generate?" → Enter 10
   # Run again later for next batch
   ```

3. **Use GPU** (if available):
   Ollama automatically uses GPU if available. Faster generation!

### **Optimization Tips:**

- **First run:** 2-3 minutes per email (includes model loading)
- **Subsequent runs:** 30-60 seconds per email
- **With GPU:** 10-20 seconds per email

---

## 📋 **Tracking Your Applications**

### **Automatic Tracking:**

After sending, update your tracking spreadsheet:

**File:** `recruiter_emails_tracking.xlsx`

**Columns to update:**
- **Date Sent:** When you sent the email
- **Status:** "Email Sent" → "Interview" → "Offer"
- **Response:** What they replied
- **Notes:** Any important info

### **Gmail Integration:**

Gmail automatically saves sent emails to "Sent" folder. Check them to verify:

1. Go to Gmail
2. Click "Sent"
3. Search: `subject:"Application"`
4. Verify all emails are there

---

## 🎁 **Advanced: Batch Processing**

### **Process 100+ Jobs**

```bash
# Batch 1: Jobs 1-25
python complete_automation.py
# When asked for batch size: 25

# Batch 2: Jobs 26-50
python complete_automation.py
# When asked for batch size: 25

# ... repeat
```

### **Automatic Scheduling (Optional)**

Windows (Task Scheduler):
```
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Daily Job Applications"
4. Trigger: Daily at 9:00 AM
5. Action: Run python complete_automation.py
```

Linux/Mac (Crontab):
```bash
crontab -e

# Add this line:
0 9 * * * cd /path/to/scripts && python complete_automation.py
```

---

## 🚀 **Quick Start Checklist**

- [ ] Ollama installed and Gwen 2.7 model downloaded
- [ ] `ollama serve` running (terminal open)
- [ ] Gmail API credentials downloaded (`gmail_credentials.json`)
- [ ] Python packages installed (`pip install requests openpyxl google-auth-oauthlib google-auth-httplib2 google-api-python-client`)
- [ ] Your resume file ready (`my_resume.pdf` or .docx or .txt)
- [ ] `jobs_cleaned.xlsx` ready (from job_data_cleaner.py)
- [ ] All Python scripts in same directory
- [ ] Run: `python complete_automation.py`

---

## 📞 **Common Questions**

**Q: Does this send from my Gmail account?**
A: Yes! It sends from your Gmail using OAuth 2.0 (secure, authorized access only).

**Q: Can I schedule automatic sends?**
A: Yes! See "Advanced: Batch Processing" section above.

**Q: How do I cancel sending?**
A: If running interactively, press Ctrl+C to stop. Already sent emails cannot be unsent.

**Q: What if Gmail blocks me?**
A: Gmail may limit sends to 100+ per day. Space out batches over multiple days.

**Q: Do I need to authorize Gmail every time?**
A: No, only first time. It saves `gmail_token.pickle` for future use.

**Q: Can I use Outlook instead of Gmail?**
A: Not with current setup. Would need different API.

**Q: What if an email fails to send?**
A: Check error message. Usually: invalid email, Gmail limits, or network issue.

---

## 🎉 **You're All Set!**

You now have a complete, automated job application system that:

✅ Reads your resume automatically
✅ Personalized emails using Ollama locally
✅ Sends via Gmail automatically
✅ Tracks everything

**Next Steps:**
1. Run: `python complete_automation.py`
2. Follow the prompts
3. Watch your emails get sent automatically!

---

Good luck! 🚀
