from django.db import models
from users.models import ClinicManager, Doctor, Patient

class Clinic(models.Model):
    clinic_name = models.CharField(max_length=255, unique=True)
    clinic_url = models.URLField(max_length=200, unique=True)
    clinic_image_url = models.URLField(max_length=200, blank=True, null=True)
    is_research_clinic = models.BooleanField(default=False)

    def __str__(self):
        return self.clinic_name
    
class ManagerClinic(models.Model):
    manager = models.OneToOneField(ClinicManager, on_delete=models.CASCADE)
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.manager} - {self.clinic if self.clinic else 'No Clinic'}"

class DoctorClinic(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    
    def __str__(self):
        return str("%s-%s" % (self.doctor, self.clinic))

class PatientClinic(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    
    def __str__(self):
        return str("%s-%s" % (self.patient, self.clinic))

