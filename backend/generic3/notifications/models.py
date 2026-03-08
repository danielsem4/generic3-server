from django.db import models
from django.utils import timezone
from clinics.models import Clinic
from users.models import Patient

eventsRepeatPeriods = (
    ('once','once'),
    ('daily','daily'),
    ('weekly','weekly'),
    ('monthly','monthly'),
)

eventsTypes = (
    ('medication', 'Medication'),
    ('activity', 'Activity'),
    ('questionnaire', 'Questionnaire'),
)
    

class EventNotificationSettings(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=eventsTypes, null=True, blank=True)
    event_id = models.IntegerField(null=True, blank=True)  # ID of the medication, activity, or questionnaire
    frequency = models.CharField(max_length=30,choices=eventsRepeatPeriods,null=True, blank=True)
    frequency_data = models.JSONField(default=list, null=True, blank=True)
    start_date_time = models.DateTimeField(default=timezone.now,null=True, blank=True)
    end_date_time = models.DateTimeField(null=True, blank=True)

