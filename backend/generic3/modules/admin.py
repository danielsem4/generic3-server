from django.contrib import admin
from .models import Modules, ClinicModules, PatientModules

admin.site.register(Modules)
admin.site.register(ClinicModules)
admin.site.register(PatientModules)
