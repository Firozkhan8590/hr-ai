from django.db import models

# Create your models here.
class jobapplication(models.Model):
    job_description=models.TextField()
    uploaded_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application for: {self.job_description[:50]}..."
class candidate(models.Model):
    application = models.ForeignKey(jobapplication, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/')
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)   
    score = models.FloatField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('interview', 'Interview Scheduled'),
        ('hired', 'Hired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Candidate: {self.name} for {self.application.id} ({self.get_status_display()})"

    
