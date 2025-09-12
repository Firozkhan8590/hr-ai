import os
import re
import pdfplumber
from docx import Document
import spacy
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from django.conf import settings
import requests

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# ---------------------------
# 1. Resume Extraction with NLP
# ---------------------------
def extract_resume(file_path):
    """
    Extract text, skills, experience, email, and keywords using NLP
    """
    text = ""
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])

    # Extract basic info
    email_match = re.findall(r"\S+@\S+", text)
    email = email_match[0] if email_match else ""
    name = text.strip().split("\n")[0] if text else "Unknown"

    # NLP keyword extraction
    doc_nlp = nlp(text.lower())
    keywords = [token.text for token in doc_nlp if token.pos_ in ['NOUN', 'PROPN'] and len(token.text) > 2]

    # Skills (can extend or load from skills database)
    skills_list = ["python", "django", "ml", "java", "sql", "react", "javascript", "html", "css"]
    skills_found = [s for s in skills_list if s.lower() in text.lower()]

    # Experience (naive extraction: look for "X years")
    experience_match = re.findall(r'(\d+)\s+years?', text.lower())
    experience = experience_match[0] + " years" if experience_match else ""

    return {
        "name": name,
        "email": email,
        "skills": skills_found,
        "experience": experience,
        "keywords": keywords,
        "text": text
    }


# ---------------------------
# 2. Candidate Ranking Using NLP Keywords
# ---------------------------
def rank_candidates(candidates, jd_text):
    """
    Rank candidates by keyword overlap with JD using NLP
    """
    doc_jd = nlp(jd_text.lower())
    jd_keywords = set([token.text for token in doc_jd if token.pos_ in ['NOUN', 'PROPN'] and len(token.text) > 2])

    for c in candidates:
        resume_keywords = set(c.get("keywords", []))
        skill_match = len(set([s.lower() for s in c.get("skills", [])]) & jd_keywords)
        keyword_match = len(resume_keywords & jd_keywords)
        experience_score = int(re.findall(r'\d+', c.get("experience", "0"))[0]) if c.get("experience") else 0

        # Weighted score formula (customizable)
        c["score"] = skill_match * 3 + keyword_match * 2 + experience_score

    return sorted(candidates, key=lambda x: x["score"], reverse=True)


# ---------------------------
# 3. Candidate Summary Generation using Gemini API
# ---------------------------
import google.generativeai as genai
from django.conf import settings

# Configure Gemini once in your app startup
genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_summary(candidate_data, jd_text):
    """
    Generate candidate summary using Google Gemini API
    """
    model = genai.GenerativeModel("gemini-1.5-flash")  # use "gemini-1.5-pro" if you need higher quality

    prompt = (
        f"Create a concise summary for a candidate applying for the following job:\n"
        f"Job Description:\n{jd_text}\n\n"
        f"Candidate Details:\n"
        f"Name: {candidate_data.get('name')}\n"
        f"Email: {candidate_data.get('email')}\n"
        f"Skills: {', '.join(candidate_data.get('skills', []))}\n"
        f"Experience: {candidate_data.get('experience')}\n\n"
        "Highlight the most relevant skills and experience for this job."
    )

    response = model.generate_content(prompt)

    return response.text.strip()



# ---------------------------
# 4. Google Calendar Interview Scheduling
# ---------------------------
import os
import logging
from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def schedule_interview(candidate_obj, slot):
    """
    Schedule interview on Google Calendar for a candidate.
    slot = {"start": "...", "end": "..."}
    """
    try:
        token_path = os.path.join(settings.BASE_DIR, "token.json")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": f"Interview with {candidate_obj.name}",
            "description": "Scheduled via HR AI System",
            "start": {"dateTime": slot["start"], "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": slot["end"], "timeZone": "Asia/Kolkata"},
            "attendees": [
                {"email": candidate_obj.email},
                {"email": "firozkhannnn8590@gmail.com"},
            ],
            "reminders": {"useDefault": True},
        }

        created_event = service.events().insert(
            calendarId="primary",
            body=event,
            sendUpdates="all"
        ).execute()

        logger.info(f"✅ Event created for {candidate_obj.email}: {created_event.get('htmlLink')}")
        return created_event.get("id")

    except FileNotFoundError:
        logger.error("❌ token.json not found in BASE_DIR")
        return None
    except HttpError as error:
        logger.error(f"❌ Google Calendar API error: {error}")
        return None
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        return None


