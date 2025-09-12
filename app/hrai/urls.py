
from django.urls import path
from . import views

urlpatterns = [
    path('',views.index,name="index"),
   
    path('post_jd/',views.post_job_and_resumes,name="post_jd"),
    path("review_candidates/<str:job_id>/",views.review_candidates,name="review_candidates"),
    path("schedule_interview/<str:job_id>/",views.schedule_interviews,name="schedule_interview"),
    path("show_candidates/",views.show_candidates,name="show_candidates"),
    path("show_interviews/",views.show_interviews_schedule,name="show_interviews"),
]