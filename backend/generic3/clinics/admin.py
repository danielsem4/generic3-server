from django.contrib import admin
from .models import Clinic, DoctorClinic, PatientClinic, ManagerClinic


admin.site.register(Clinic)
admin.site.register(DoctorClinic)
admin.site.register(PatientClinic)
admin.site.register(ManagerClinic)
