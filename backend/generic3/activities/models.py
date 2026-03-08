from django.db import models
from django.utils import timezone

from clinics.models import Clinic
from users.models import Doctor, Patient

activitiesRepeatPeriods = (
    ('once','once'),
    ('daily','daily'),
    ('weekly','weekly'),
    ('monthly','monthly'),
)

class Activity(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    
class ClinicActivity(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.activity.name}"
    
class PatientActivity(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    frequency       = models.CharField(max_length=30,
                                       choices=activitiesRepeatPeriods,
                                        default='once',)
    frequency_data  = models.JSONField(default=list, null=True, blank=True)
    start_date      = models.DateTimeField(default=timezone.now)
    end_date        = models.DateTimeField(default=timezone.datetime(2100, 1, 1))

    def __str__(self):
        return f"{self.activity.name} for Patient {self.patient.user.first_name} {self.patient.user.last_name}"

class ActivityReport(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
class ActivitiesBundle(models.Model):
    bundle_name = models.CharField(max_length=255)
    activities = models.ManyToManyField(Activity , related_name='bundled_activities') 
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    
class PatientActivitiesBundle(models.Model): 
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE , related_name="patient_activity_bundles")
    bundle = models.ForeignKey(ActivitiesBundle, on_delete=models.CASCADE , related_name="patient_activity_bundles")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE , related_name="doctor_activity_bundles")