#!/usr/bin/env python3
"""
Job Application Automation - UI
Flow: Upload Seek JSON -> Clean -> Score (Ollama) -> pick jobs
      -> generate emails (Ollama, editable) -> attach resume -> send (GmaAil)

This UI only CALLS your existing scripts. It does not modify them.
Place this file in the SAME folder as:
    job_data_cleaner.py
    resume_parser.py
    gmail_automation.py
and (optionally) your resume + gmail_credentials.json
"""

import os
import re
import json
import tempfile
import requests
import streamlit as st

# --- import your existing, working scripts (no changes made to them) ---
from job_data_cleaner import process_job_data, create_xlsx
from resume_parser import parse_resume
import gmail_automation as gmail

# ---------------------------------------------------------------------------
# CONFIG  (matches your ollama_email_generator.py)
# ---------------------------------------------------------------------------
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
OLLAMA_GEN_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"   # same default as your generator; editable in sidebar

st.set_page_config(page_title="Job Application Automation", page_icon="tgt", layout="wide")

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("cleaned_jobs", [])       # list of dicts from process_job_data
ss.setdefault("resume_data", None)      # dict from parse_resume
ss.setdefault("resume_path", None)      # path on disk for attaching
ss.setdefault("scores", {})             # job_id -> int
ss.setdefault("emails", {})             # job_id -> {"subject":..., "body":...}
ss.setdefault("sent", {})               # job_id -> True
ss.setdefault("model", OLLAMA_MODEL)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def ollama_up(model):
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=5)
        if r.status_code != 200:
            return False, "Ollama responded but not with 200. Is it healthy?"
        names = [m["name"] for m in r.json().get("models", [])]
        if model not in names:
            return False, f"Model '{model}' not found. Installed: {', '.join(names) or 'none'}"
        return True, "ok"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Ollama. Run: ollama serve"
    except Exception as e:
        return False, str(e)


def ollama_generate(prompt, model, timeout=180):
    r = requests.post(
        OLLAMA_GEN_URL,
        json={"model": model, "prompt": prompt, "stream": False,
              "options": {"temperature": 0.7, "top_p": 0.9}},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def score_prompt(job, resume):
    skills = ", ".join(resume.get("technical_stack", [])[:12])
    return (
        "You are screening a job for a candidate. Reply with ONLY an integer 0-100 "
        "representing fit. No words.\n\n"
        f"CANDIDATE: {resume.get('experience_years','?')} yrs experience. Skills: {skills}\n"
        f"JOB TITLE: {job.get('job_title','')}\n"
        f"COMPANY: {job.get('company_name','')}\n"
        f"TECH: {job.get('tech_stack','')}\n"
        f"HOOK: {job.get('job_hook','')}\n"
        f"REQUIREMENTS: {job.get('essential_requirements','')[:400]}\n\n"
        "Score (0-100):"
    )


def parse_score(text):
    m = re.search(r"\d{1,3}", text or "")
    if not m:
        return 0
    return max(0, min(100, int(m.group())))


def email_prompt(job, resume, profile):
    skills = ", ".join(resume.get("technical_stack", [])[:10])
    return (
        "Write a concise, professional job application email. "
        "Output EXACTLY in this format and nothing else:\n"
        "SUBJECT: <one line>\n"
        "<blank line>\n"
        "<body starting with 'Dear Hiring Team,' and ending with a sign-off>\n\n"
        f"POSITION: {job.get('job_title','')} at {job.get('company_name','')}\n"
        f"COMPANY FOCUS: {job.get('job_hook','')} {job.get('company_focus','')}\n"
        f"KEY REQUIREMENTS: {job.get('essential_requirements','')[:400]}\n"
        f"TECH STACK: {job.get('tech_stack','')}\n\n"
        f"APPLICANT NAME: {profile['name']}\n"
        f"APPLICANT PHONE: {profile['phone']}\n"
        f"APPLICANT EMAIL: {profile['email']}\n"
        f"APPLICANT SKILLS: {skills}\n"
        f"APPLICANT EXPERIENCE: {resume.get('experience_years','')} years\n\n"
        "Keep it under 200 words. Use the applicant's real name/phone/email in the sign-off "
        "(no placeholders)."
    )


def split_subject_body(text, fallback_subject):
    subject, body_lines, in_body = "", [], False
    for line in (text or "").splitlines():
        if not in_body and line.strip().upper().startswith("SUBJECT:"):
            subject = line.split(":", 1)[1].strip()
            in_body = True
            continue
        if in_body:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not subject:
        subject = fallback_subject
    if not body:
        body = (text or "").strip()
    return subject, body


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Setup")
    ss.model = st.text_input("Ollama model", value=ss.model)
    up, msg = ollama_up(ss.model)
    if up:
        st.success("Ollama: connected")
    else:
        st.error(f"Ollama: {msg}")

    st.divider()
    st.caption("Profile used in email sign-off")
    profile = {
        "name": st.text_input("Name", "Akshaya Agarwal"),
        "phone": st.text_input("Phone", "+61 469 838 346"),
        "email": st.text_input("Email", "akshayaakshaya2000@gmail.com"),
    }

    st.divider()
    st.caption("Resume (parsed for matching + attached to emails)")
    resume_upload = st.file_uploader("Resume (.pdf/.docx/.txt)", type=["pdf", "docx", "txt"])
    if resume_upload and st.button("Parse resume"):
        suffix = os.path.splitext(resume_upload.name)[1]
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(resume_upload.getbuffer())
        ss.resume_path = path
        ss.resume_data = parse_resume(path)
        if ss.resume_data:
            st.success(f"Parsed: {ss.resume_data.get('name','(no name)')}")
        else:
            st.error("Could not parse resume")

st.title("Job Application Automation")

# ---------------------------------------------------------------------------
# STEP 1: UPLOAD + CLEAN
# ---------------------------------------------------------------------------
st.header("1. Upload Seek JSON")
json_upload = st.file_uploader("Seek scraper JSON", type="json")

if json_upload and st.button("Clean & load jobs"):
    try:
        data = json.load(json_upload)          # reads uploaded buffer directly (UTF-8 safe)
        ss.cleaned_jobs = process_job_data(data)
        ss.scores, ss.emails, ss.sent = {}, {}, {}
        create_xlsx(ss.cleaned_jobs, "jobs_cleaned.xlsx")
        st.success(f"Loaded {len(ss.cleaned_jobs)} jobs and wrote jobs_cleaned.xlsx")
    except Exception as e:
        st.error(f"Failed to read/clean JSON: {e}")

if ss.cleaned_jobs:
    st.caption(f"{len(ss.cleaned_jobs)} jobs loaded")

# ---------------------------------------------------------------------------
# STEP 2: SCORE
# ---------------------------------------------------------------------------
st.header("2. Score against your resume (Ollama)")

if not ss.cleaned_jobs:
    st.info("Upload and clean a JSON first.")
elif not ss.resume_data:
    st.info("Parse your resume in the sidebar first.")
else:
    if st.button("Score all jobs"):
        ok, msg = ollama_up(ss.model)
        if not ok:
            st.error(msg)
        else:
            bar = st.progress(0.0)
            for i, job in enumerate(ss.cleaned_jobs):
                try:
                    txt = ollama_generate(score_prompt(job, ss.resume_data), ss.model, timeout=90)
                    ss.scores[str(job["job_id"])] = parse_score(txt)
                except Exception as e:
                    ss.scores[str(job["job_id"])] = 0
                    st.warning(f"Score failed for {job.get('job_title','?')}: {e}")
                bar.progress((i + 1) / len(ss.cleaned_jobs))
            st.success("Scoring complete")

# ---------------------------------------------------------------------------
# STEP 3: PICK JOBS
# ---------------------------------------------------------------------------
st.header("3. Choose jobs to apply to")

chosen = []
if ss.cleaned_jobs:
    min_score = st.slider("Only show jobs scoring at least", 0, 100, 0)
    for job in ss.cleaned_jobs:
        jid = str(job["job_id"])
        score = ss.scores.get(jid)
        if score is not None and score < min_score:
            continue
        shown = score if score is not None else "-"
        label = f"[{shown}] {job.get('job_title','')} - {job.get('company_name','')} - {job.get('contact_email','')}"
        if st.checkbox(label, key=f"pick_{jid}"):
            chosen.append(job)

# ---------------------------------------------------------------------------
# STEP 4: GENERATE EMAILS (editable)
# ---------------------------------------------------------------------------
st.header("4. Generate & edit emails")

if chosen and st.button(f"Generate emails for {len(chosen)} selected job(s)"):
    ok, msg = ollama_up(ss.model)
    if not ok:
        st.error(msg)
    else:
        bar = st.progress(0.0)
        for i, job in enumerate(chosen):
            jid = str(job["job_id"])
            fallback = f"Application for {job.get('job_title','')} at {job.get('company_name','')}"
            try:
                raw = ollama_generate(email_prompt(job, ss.resume_data, profile), ss.model)
                subject, body = split_subject_body(raw, fallback)
            except Exception as e:
                subject, body = fallback, f"(generation failed: {e})"
            ss.emails[jid] = {"subject": subject, "body": body}
            bar.progress((i + 1) / len(chosen))
        st.success("Emails generated. Edit below, then send.")

# ---------------------------------------------------------------------------
# STEP 5: EDIT + SEND (per email)
# ---------------------------------------------------------------------------
st.header("5. Review, attach resume & send")

attach = st.checkbox("Attach resume to each email", value=True)
if attach and not ss.resume_path:
    st.warning("No resume uploaded - parse a resume in the sidebar to attach it.")

selected_ids = {str(j["job_id"]) for j in chosen}
to_show = [j for j in ss.cleaned_jobs
           if str(j["job_id"]) in ss.emails and str(j["job_id"]) in selected_ids]

if not to_show:
    st.info("Generate emails for your selected jobs to see them here.")
else:
    for job in to_show:
        jid = str(job["job_id"])
        default_to = job.get("contact_email", "") or ""
        with st.expander(f"{job.get('job_title','')} - {job.get('company_name','')}", expanded=False):
            rec = st.text_input("To", value=default_to, key=f"to_{jid}")
            subj = st.text_input("Subject", value=ss.emails[jid]["subject"], key=f"su_{jid}")
            body = st.text_area("Body", value=ss.emails[jid]["body"], height=260, key=f"bo_{jid}")
            ss.emails[jid] = {"subject": subj, "body": body}

            col1, col2 = st.columns([1, 3])
            with col1:
                send_click = st.button("Send", key=f"send_{jid}")
            with col2:
                if ss.sent.get(jid):
                    st.success("Sent")

            if send_click:
                if "@" not in rec:
                    st.error("Recipient email looks invalid.")
                else:
                    try:
                        if not gmail.setup_gmail_credentials():
                            st.error("gmail_credentials.json missing in this folder.")
                        else:
                            creds = gmail.authenticate_gmail()
                            service = gmail.get_gmail_service(creds)
                            ok_send, result = gmail.send_email(
                                service, rec, subj, body,
                                attachment_path=ss.resume_path if attach else None,
                            )
                            if ok_send:
                                ss.sent[jid] = True
                                st.success(f"Sent to {rec} (id {str(result)[:12]})")
                            else:
                                st.error(f"Send failed: {result}")
                    except Exception as e:
                        st.error(f"Send failed: {e}")

st.divider()
st.caption(f"Loaded {len(ss.cleaned_jobs)} | Scored {len(ss.scores)} | "
           f"Drafted {len(ss.emails)} | Sent {sum(ss.sent.values())}")