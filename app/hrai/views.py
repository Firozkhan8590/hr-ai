from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import jobapplication, candidate
from .utils import extract_resume, rank_candidates, generate_summary, schedule_interview

def index(request):
    total_jobs = jobapplication.objects.count()
    pending_reviews = candidate.objects.filter(status="under_review").count()
    scheduled_interviews = candidate.objects.filter(status="interview").count()

    context = {
        "total_jobs": total_jobs,
        "pending_reviews": pending_reviews,
        "scheduled_interviews": scheduled_interviews,
    }
    return render(request, "index.html", context)

# ---------------------------
# 1. HR posts Job Description
# ---------------------------
def post_job_and_resumes(request):
    
    if request.method == "POST":
        jd_text = request.POST.get("job_description", "")
        resumes = request.FILES.getlist("resumes")

        if jd_text:
            # Create job application
            job = jobapplication.objects.create(job_description=jd_text)

            # Loop through uploaded resumes
            for f in resumes:
                cand = candidate.objects.create(application=job, resume=f, name=f.name)
                resume_data = extract_resume(cand.resume.path)
                cand.name = resume_data.get("name", cand.name)
                cand.summary = ""  # Summary will be generated later
                cand.save()

            # Redirect to review candidates
            return redirect("review_candidates", job_id=job.id)

    return render(request, "jd.html")



# ---------------------------
# 3. Review & Rank Candidates
# ---------------------------
def review_candidates(request, job_id):
    job = jobapplication.objects.get(id=job_id)
    candidates_qs = candidate.objects.filter(application=job)

    # Prepare candidates for ranking
    candidates_list = []
    for c in candidates_qs:
        resume_data = extract_resume(c.resume.path)
        candidates_list.append({
            "id": c.id,
            "name": resume_data.get("name", c.name),
            "email": resume_data.get("email", ""),
            "skills": resume_data.get("skills", []),
            "experience": resume_data.get("experience", ""),
            "keywords": resume_data.get("keywords", []),
            "score": 0
        })

    # Rank candidates using NLP
    ranked_candidates = rank_candidates(candidates_list, job.job_description)

    # Update DB and generate Gemini summaries
    # Update DB and generate Gemini summaries
    for c_data in ranked_candidates:
        c_obj = candidate.objects.get(id=c_data["id"])

        # ✅ Save email if extracted
        if c_data.get("email") and not c_obj.email:
            c_obj.email = c_data["email"]

        c_obj.score = c_data["score"]
        c_obj.summary = generate_summary(c_data, job.job_description)

        if c_obj.score >= 7:
            c_obj.status = "shortlisted"
        else:
            c_obj.status = "rejected"

        c_obj.save()


    candidates_qs = candidate.objects.filter(application=job).order_by("-score")

    has_shortlisted = candidates_qs.filter(status="shortlisted").exists()
    

    return render(request, "review_candidates.html", {
        "job": job,
        "candidates": candidates_qs,
        "has_shortlisted":has_shortlisted
    })


# ---------------------------
# 4. Schedule Interviews
# ---------------------------
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
import logging
from datetime import datetime

logger = logging.getLogger(__name__)  # Django logging

def schedule_interviews(request, job_id):
    job = jobapplication.objects.get(id=job_id)

    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_candidates")
        print("Selected candidate IDs:", selected_ids)

        # Get datetime from form
        slot_start_str = request.POST.get("slot_start")  # e.g., "2025-09-15T10:00"
        slot_end_str = request.POST.get("slot_end")      # e.g., "2025-09-15T10:30"

        # Convert to ISO 8601 with seconds
        slot_start = datetime.strptime(slot_start_str, "%Y-%m-%dT%H:%M").isoformat()
        slot_end = datetime.strptime(slot_end_str, "%Y-%m-%dT%H:%M").isoformat()

        logger.debug(f"Selected candidates: {selected_ids}")
        logger.debug(f"Slot: {slot_start} - {slot_end}")

        results = []  # Collect results for display

        for cand_id in selected_ids:
            cand = candidate.objects.get(id=cand_id)
            
            if not cand.email:
                logger.warning(f"Candidate {cand.id} has no email. Skipping.")
                results.append(f"{cand.name} ({cand.id}): No email, skipped")
                continue

            slot = {"start": slot_start, "end": slot_end}

            try:
                event_id = schedule_interview(cand, slot)
                if event_id:
                    logger.info(f"Google Calendar event created for {cand.email}")
                    results.append(f"{cand.name} ({cand.email}): Event created successfully")
                else:
                    logger.warning(f"Failed to create event for {cand.email}")
                    results.append(f"{cand.name} ({cand.email}): Event creation failed")
            except Exception as e:
                logger.exception(f"Error scheduling Google Calendar for {cand.email}: {e}")
                results.append(f"{cand.name} ({cand.email}): Error occurred")

            # Update candidate status
            cand.status = "interview"
            cand.save()

        print(results)
        return HttpResponse("<br>".join(results))

    # Only shortlisted candidates
    candidates_qs = candidate.objects.filter(application=job, status='shortlisted').order_by("-score")
    return render(request, "review_candidates.html", {
        "job": job,
        "candidates": candidates_qs
    })



def show_candidates(request):
    candidates=candidate.objects.all().order_by("-score")
    return render(request,"show_candidates.html",{"candidates":candidates})
def show_interviews_schedule(request):
    interviews=candidate.objects.filter(status="interview").order_by("-score")
    return render(request,"show_interviews.html",{"interviews":interviews})
