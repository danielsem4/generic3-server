from django.db import models
from users.models import Patient
from clinics.models import Clinic

class Modules(models.Model):
    module_name = models.CharField(max_length=150, blank=True)
    module_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.module_name) 


class ClinicModules(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    module = models.ForeignKey(Modules, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str("{}-{}".format(self.clinic,self.module))

class PatientModules(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    module = models.ForeignKey(Modules, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str("{}-{}".format(self.patient, self.module))