from django.db import models
from clinics.models import Clinic
from users.models import Patient , Doctor

class SharedFiles(models.Model):
    file_name = models.CharField(('file name'), max_length=1000, blank=False)
    file_path = models.CharField(('file path'), max_length=1000, blank=False)
    size = models.IntegerField(null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name