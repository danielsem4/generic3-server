from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db import models

user_role = (
    ('ADMIN', 'Admin'),
    ('CLINIC_MANAGER', 'Clinic Manager'),
    ('DOCTOR', 'Doctor'),
    ('PATIENT', 'Patient'),
    ('RESEARCH_PATIENT', 'Research Patient'),
)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=30, choices=user_role, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    

class ClinicManager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    def __str__(self):
        return f"{self.user}"
    
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    def __str__(self):
        return f"{self.user}"
    
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    def __str__(self):
        return f"{self.user}"
    
class PatientDoctor(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.patient} - {self.doctor}"
