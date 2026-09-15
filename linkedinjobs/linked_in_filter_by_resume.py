#!/usr/bin/env python3
"""
LinkedIn Filter by Resume - Filter jobs in Excel based on resume match using Ollama
Uses Ollama to intelligently match your resume against job postings
"""

import sys
import os
import json
import requests
from openpyxl import load_workbook, Workbook
from resume_parser import parse_resume
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = 'llama3.1:8b'

# Your details
YOUR_NAME = "Akshaya Agarwal"
YOUR_PHONE = "+61 469 838 346"

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
def parse_resume(resume_file):
    """Parse resume file"""
    try:
        from resume_parser import parse_resume
        resume_data = parse_resume(resume_file)
        if resume_data:
            return resume_data
    except ImportError:
        pass
    except Exception as e:
        pass
    return None
    
    return None

def extract_seniority_info(job_data):
    """Extract seniority level and experience requirements from job data"""
    job_title = (job_data.get('job_title') or job_data.get('job title', '')).lower()
    job_description = (job_data.get('job_description') or job_data.get('description') or '').lower()
    requirements = (job_data.get('requirements') or '').lower()
    seniority = (job_data.get('seniority_level') or '').lower()
    employment_type = (job_data.get('employment_type') or '').lower()
    job_function = (job_data.get('job_function') or '').lower()
    
    # Check for senior-level indicators in title
    senior_title_keywords = [
        'senior', 'lead', 'principal', 'staff', 'architect', 'manager', 'director',
        'head of', 'vp', 'vice president', 'chief', 'technical lead', 'team lead',
        'engineering lead', 'tech lead'
    ]
    
    # Check for years of experience requirements
    import re
    exp_patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
        r'minimum\s*(?:of\s*)?(\d+)\s*years?',
        r'at least\s*(\d+)\s*years?',
        r'(\d+)\s*years?\s*experience',
        r'experience.*?(\d+)\s*years?',
        r'required.*?(\d+)\s*years?'
    ]
    
    max_required_years = 0
    text_to_search = job_description + ' ' + requirements
    for pattern in exp_patterns:
        matches = re.findall(pattern, text_to_search)
        for match in matches:
            try:
                years = int(match)
                max_required_years = max(max_required_years, years)
            except:
                pass
    
    # Check seniority field
    seniority_keywords = ['senior', 'lead', 'principal', 'staff', 'expert', 'architect']
    is_senior_by_field = any(kw in seniority for kw in seniority_keywords)
    
    # Check title
    is_senior_by_title = any(kw in job_title for kw in senior_title_keywords)
    
    # Check for "super senior" - 8+ years or principal/staff/architect
    super_senior_keywords = ['principal', 'staff', 'architect', 'distinguished', 'fellow', 'vp engineering', 'director']
    is_super_senior = any(kw in job_title for kw in super_senior_keywords) or max_required_years >= 8
    
    return {
        'max_required_years': max_required_years,
        'is_senior_by_title': is_senior_by_title,
        'is_senior_by_field': is_senior_by_field,
        'is_super_senior': is_super_senior,
        'seniority_raw': seniority,
        'title_raw': job_title
    }


def score_job_with_ollama(job_data, resume_data):
    """Score a job using Ollama based on resume match"""
    
    # Handle both underscore and space versions of column names
    job_title = job_data.get('job_title') or job_data.get('job title', 'Job')
    company = job_data.get('company_name') or job_data.get('company', 'Unknown')
    job_description = (job_data.get('job_description') or job_data.get('description') or '')[:800]
    requirements = job_data.get('requirements', '')[:800]
    job_function = job_data.get('job_function', '')[:200]
    seniority = job_data.get('seniority_level', 'Not specified')
    
    user_skills = ', '.join(resume_data.get('technical_stack', [])[:15])
    user_experience = resume_data.get('experience_years', 'several')
    user_summary = resume_data.get('summary', '')[:300]
    
    # Extract seniority info for the prompt
    seniority_info = extract_seniority_info(job_data)
    
    prompt = f"""Analyze how well this candidate matches this job. Be concise but accurate.

CANDIDATE PROFILE:
Name: {YOUR_NAME}
Experience: {user_experience}+ years (approximately 2 years)
Summary: {user_summary}
Skills: {user_skills}

JOB POSTING:
Company: {company}
Title: {job_title}
Function: {job_function}
Seniority Level: {seniority}
Description: {job_description}
Requirements: {requirements}

DETECTED SENIORITY INFO:
- Years required: {seniority_info['max_required_years']}+ years
- Is senior title: {seniority_info['is_senior_by_title']}
- Is super senior (principal/staff/architect/8+ years): {seniority_info['is_super_senior']}

CRITICAL FILTERING RULES - APPLY THESE STRICTLY:
1. If job requires 5+ years experience AND candidate has only 2 years -> Score LOW (30-40), recommendation SKIP
2. If job is "super senior" (principal, staff, architect, 8+ years) -> Score VERY LOW (10-20), recommendation SKIP
3. If job is "senior" (3-5 years) -> Score MODERATE (40-55), recommendation CONSIDER only if strong skill match
4. If job is "mid-level" (2-3 years) or "junior" (0-2 years) -> Score normally based on skill match
5. Prefer jobs with 0-3 years requirement or "not applicable" seniority

Provide ONLY a JSON response (no other text):
{{
  "score": <0-100 as integer>,
  "match_level": "<EXCELLENT|GOOD|FAIR|POOR>",
  "strengths": [<list 2-3 key strengths>],
  "gaps": [<list 2-3 key gaps if any>],
  "recommendation": "<APPLY|CONSIDER|SKIP>",
  "reason": "<1 line explanation>",
  "experience_match": "<YES|NO|PARTIAL>"
}}

Use these guidelines:
- 90-100: Excellent match (APPLY) - skills match + experience appropriate
- 75-89: Good match (APPLY) - strong skill match, experience close
- 60-74: Fair match (CONSIDER) - some skill gaps or slight experience mismatch
- Below 60: Poor match (SKIP) - major gaps or experience mismatch

For seniority mismatch (candidate 2yrs vs job 5+yrs): CAP at 40, SKIP
For super senior roles: CAP at 20, SKIP

Respond ONLY with the JSON, no markdown, no explanation."""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.5,
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Try to extract JSON
            try:
                score_data = json.loads(response_text)
                return score_data
            except:
                # If JSON parsing fails, try to extract score
                import re
                score_match = re.search(r'"score":\s*(\d+)', response_text)
                if score_match:
                    score = int(score_match.group(1))
                    return {
                        "score": score,
                        "match_level": "GOOD" if score >= 75 else "FAIR",
                        "recommendation": "APPLY" if score >= 75 else "CONSIDER",
                        "reason": "Scored by Ollama"
                    }
        
        return {"score": 50, "recommendation": "ERROR", "reason": "Ollama error"}
        
    except Exception as e:
        print(f"❌ Error scoring with Ollama: {str(e)}")
        return {"score": 50, "recommendation": "ERROR", "reason": str(e)}

def filter_jobs_excel(excel_file, resume_file, min_score=60, output_file=None, max_rows=None):
    """Filter jobs in Excel based on resume match"""
    
    print(f"\n{'='*80}")
    print("RESUME-BASED JOB FILTER")
    print(f"{'='*80}\n")
    
    # Check Ollama
    if not check_ollama_connection():
        return False
    
    # Parse resume
    resume_data = parse_resume(resume_file)
    if not resume_data:
        return False
    
    # Load Excel
    print(f"\n📂 Reading Excel file: {excel_file}")
    try:
        wb = load_workbook(excel_file)
        ws = wb.active
        print(f"📄 Sheet: {ws.title}")
    except Exception as e:
        print(f"❌ Error reading Excel: {str(e)}")
        return False
    
    # Find columns (case-insensitive)
    headers = {}
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value:
            headers[cell.value.lower()] = col_idx
    
    print("\n🔍 Detected columns in your Excel:")
    for col_name in list(headers.keys())[:10]:  # Show first 10
        print(f"   ✓ {col_name}")
    if len(headers) > 10:
        print(f"   ... and {len(headers) - 10} more\n")
    
    # Read jobs
    jobs = []
    print(f"\n📋 Reading job data...")
    
    for row_idx in range(2, ws.max_row + 1):
        job_data = {}
        for header_name, col_idx in headers.items():
            value = ws.cell(row=row_idx, column=col_idx).value
            job_data[header_name] = value if value else ""
        
        # Check for job title (handles both formats)
        if job_data.get('job_title') or job_data.get('job title') or job_data.get('title'):
            jobs.append((row_idx, job_data))
        
        if max_rows is not None and len(jobs) >= max_rows:
            break
    
    print(f"✓ Found {len(jobs)} jobs\n")
    
    # Score jobs
    print(f"{'='*80}")
    print(f"SCORING {len(jobs)} JOBS WITH OLLAMA")
    print(f"{'='*80}\n")
    
    scored_jobs = []
    
    for idx, (row_idx, job_data) in enumerate(jobs, 1):
        job_title = job_data.get('job title') or job_data.get('title', 'Job')
        company = job_data.get('company', 'Unknown')
        
        print(f"[{idx}/{len(jobs)}] {job_title} at {company}")
        
        score_data = score_job_with_ollama(job_data, resume_data)
        
        score = score_data.get('score', 50)
        recommendation = score_data.get('recommendation', 'SKIP')
        reason = score_data.get('reason', '')
        
        print(f"   Score: {score}/100 | {recommendation} | {reason}\n")
        
        scored_jobs.append({
            'row': row_idx,
            'job_data': job_data,
            'score': score,
            'recommendation': recommendation,
            'reason': reason
        })
    
    # Filter by score
    print(f"{'='*80}")
    print(f"FILTERING RESULTS")
    print(f"{'='*80}\n")
    
    filtered = [j for j in scored_jobs if j['score'] >= min_score]
    
    print(f"📊 Statistics:")
    print(f"   Total jobs: {len(scored_jobs)}")
    print(f"   Filtered (score >= {min_score}): {len(filtered)}")
    print(f"   Filtered out: {len(scored_jobs) - len(filtered)}")
    
    by_recommendation = {}
    for job in scored_jobs:
        rec = job['recommendation']
        by_recommendation[rec] = by_recommendation.get(rec, 0) + 1
    
    print(f"\n📈 By Recommendation:")
    for rec, count in sorted(by_recommendation.items(), key=lambda x: -x[1]):
        print(f"   {rec}: {count}")
    
    # Create output Excel
    if output_file is None:
        output_file = excel_file.replace('.xlsx', '_filtered.xlsx')
    
    print(f"\n💾 Creating filtered Excel: {output_file}")
    
    # Sort by score (highest first)
    filtered.sort(key=lambda x: -x['score'])
    
    # Create new workbook
    new_wb = Workbook()
    new_ws = new_wb.active
    new_ws.title = "Filtered Jobs"
    
    # Headers
    new_headers = ['Score', 'Recommendation', 'Reason'] + list(headers.keys())
    for col_idx, header in enumerate(new_headers, 1):
        cell = new_ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    
    # Add data
    for row_idx, job in enumerate(filtered, 2):
        # Score
        score = job['score']
        score_cell = new_ws.cell(row=row_idx, column=1, value=score)
        
        # Color by score
        if score >= 80:
            score_cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
        elif score >= 70:
            score_cell.fill = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid")
        else:
            score_cell.fill = PatternFill(start_color="FFB6C6", end_color="FFB6C6", fill_type="solid")
        
        # Recommendation & Reason
        new_ws.cell(row=row_idx, column=2, value=job['recommendation'])
        new_ws.cell(row=row_idx, column=3, value=job['reason'])
        
        # Job data - preserve original column names from headers
        for col_idx, (header_lower, original_col) in enumerate(headers.items(), 4):
            value = job['job_data'].get(header_lower, '')
            new_ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Set column widths
    new_ws.column_dimensions['A'].width = 10
    new_ws.column_dimensions['B'].width = 12
    new_ws.column_dimensions['C'].width = 30
    
    new_wb.save(output_file)
    
    print(f"✅ Filtered Excel created: {output_file}")
    print(f"\n🟢 GREEN (80+): High match - Apply immediately")
    print(f"🟡 YELLOW (70-79): Good match - Apply")
    print(f"🔴 RED (Below 70): Fair match - Consider")
    
    print(f"\n{'='*80}")
    print(f"✅ FILTERING COMPLETE")
    print(f"{'='*80}\n")
    
    print(f"Next steps:")
    print(f"1. Open filtered file: {output_file}")
    print(f"2. Use url_batch_opener.py to open Apply URLs:")
    print(f"   python url_batch_opener.py {output_file} 15")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: python linkedin_filter_by_resume.py <excel_file> <resume_file> [min_score] [output_file] [--max-rows N]")
        print("\nExamples:")
        print("  python linkedin_filter_by_resume.py jobs.xlsx my_resume.pdf")
        print("  python linkedin_filter_by_resume.py jobs.xlsx my_resume.pdf 70")
        print("  python linkedin_filter_by_resume.py jobs.xlsx my_resume.pdf 75 filtered_jobs.xlsx")
        print("  python linkedin_filter_by_resume.py jobs.xlsx my_resume.pdf 60 --max-rows 2")
        print("\nOptions:")
        print("  min_score: Minimum match score (0-100, default 60)")
        print("  output_file: Name of filtered Excel file")
        print("  --max-rows N: Only score the first N jobs (default: all)")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    resume_file = sys.argv[2]
    min_score = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 60
    output_file = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else None
    
    max_rows = None
    if '--max-rows' in sys.argv:
        idx = sys.argv.index('--max-rows')
        if idx + 1 < len(sys.argv):
            max_rows = int(sys.argv[idx + 1])
        else:
            print("❌ --max-rows requires a value")
            sys.exit(1)
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        sys.exit(1)
    
    if not os.path.exists(resume_file):
        print(f"❌ Resume file not found: {resume_file}")
        sys.exit(1)
    
    success = filter_jobs_excel(excel_file, resume_file, min_score, output_file, max_rows)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()