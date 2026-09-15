# ⚡ Quick Reference: Filter & Open URLs

---

## 🎯 **2-Step Process**

### **Step 1: Filter Excel by Resume Match (Using Ollama)**

```bash
python linkedin_filter_by_resume.py jobs.xlsx resume.pdf 75
```

**What it does:**
- Reads 1000+ jobs from Excel
- Uses Ollama to score each against your resume
- Keeps only score 75+ (best matches)
- Creates `jobs_filtered.xlsx`

**Time:** 5-30 minutes (depending on job count)

**Output:** Excel sorted by score (highest first)

---

### **Step 2: Open URLs in Chrome Batches**

```bash
python url_batch_opener.py jobs_filtered.xlsx 15
```

**What it does:**
- Opens 15 URLs at a time in Chrome
- Each in a new tab
- Waits for you to press ENTER between batches
- Continues until all opened

**Time:** 10 seconds per batch

**Output:** Chrome with 15 job tabs open

---

## 📋 **Commands Reference**

### **Filter Commands**

```bash
# Default (score >= 60)
python linkedin_filter_by_resume.py jobs.xlsx resume.pdf

# Only high matches (score >= 75)
python linkedin_filter_by_resume.py jobs.xlsx resume.pdf 75

# Custom output file
python linkedin_filter_by_resume.py jobs.xlsx resume.pdf 75 my_filtered.xlsx
```

### **URL Opener Commands**

```bash
# Interactive - choose batch size
python url_batch_opener.py jobs.xlsx

# 10 per batch
python url_batch_opener.py jobs.xlsx 10

# 15 per batch
python url_batch_opener.py jobs.xlsx 15

# 20 per batch
python url_batch_opener.py jobs.xlsx 20

# Start from row 50
python url_batch_opener.py jobs.xlsx 15 50
```

---

## 📊 **Expected Flow**

```
5000 Jobs
    ↓
Filter (score 75+)
    ↓
950 Filtered Jobs
    ↓
Open 15 at a time
    ↓
Batch 1: Jobs 1-15 ✅
Batch 2: Jobs 16-30 ✅
Batch 3: Jobs 31-45 ✅
...
Batch 63: Jobs 931-945 ✅
    ↓
Done!
```

---

## 🎨 **Color Coding**

After filtering, Excel shows:

```
🟢 Green (80+)    - Excellent match → APPLY NOW
🟡 Yellow (70-79) - Good match → APPLY
🔴 Red (<70)      - Fair match → CONSIDER
```

---

## ⚙️ **Requirements Checklist**

- [ ] Ollama running: `ollama serve`
- [ ] Your resume file ready (PDF/DOCX/TXT)
- [ ] Excel with "Apply URL" column
- [ ] Python packages: `pip install -r requirements.txt`
- [ ] Google Chrome installed

---

## 🚀 **Complete Example**

### **You have:** `linkedin_jobs_2000.xlsx` (2000 jobs)

```bash
# Step 1: Filter to best matches only
python linkedin_filter_by_resume.py linkedin_jobs_2000.xlsx my_resume.pdf 75

Output:
Total: 2000 jobs
Filtered: 450 jobs (75+ score)
File: linkedin_jobs_2000_filtered.xlsx
```

```bash
# Step 2: Open top batch
python url_batch_opener.py linkedin_jobs_2000_filtered.xlsx 15

Browser opens: 15 job tabs
Press ENTER to see next 15
Continue...
```

---

## 💡 **Tips**

1. **Start conservative** - Use score 75+ first time
2. **Review score reasons** - See why each job scored as it did
3. **Adjust batch size** - Use 10 if slow, 20 if fast
4. **Take breaks** - 15 jobs per batch = time to review each
5. **Save filtered file** - Reuse filtered Excel multiple times

---

## 🎯 **Typical Timeline**

```
Filter 2000 jobs:        15 minutes
Open 450 filtered jobs:  
  - 450 ÷ 15 = 30 batches
  - 30 batches × 1 min each = 30 minutes
  - Plus time to review/apply: 2-3 hours

Total: Apply to 450 jobs = 3-4 hours
```

---

## ❌ **Common Issues**

### **"Cannot connect to Ollama"**
→ Run: `ollama serve` in another terminal

### **"Apply URL column not found"**
→ Make sure Excel has column with "url" in name

### **Chrome doesn't open**
→ Make sure Chrome is installed and default browser

### **Score takes too long**
→ It's normal! Ollama analyzes each job. Grab coffee ☕

---

## ✅ **Success Metrics**

```
✅ 450+ jobs filtered (best matches only)
✅ All URLs opened in Chrome (15 at a time)
✅ Each job in separate tab (easy to review)
✅ Ready to apply immediately
✅ Time saved vs manually opening each: 10+ hours!
```

---

## 🚀 **You're Ready!**

**Start with:**

```bash
python linkedin_filter_by_resume.py jobs.xlsx resume.pdf 75
```

**Then:**

```bash
python url_batch_opener.py jobs_filtered.xlsx 15
```

**Go apply!** 💼

---

For full guide: See `FILTER_AND_OPEN_GUIDE.md`