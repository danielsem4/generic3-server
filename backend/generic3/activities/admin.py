from django.contrib import admin
from .models import Activity, ActivityReport, ClinicActivity, PatientActivity , ActivityReport, ActivitiesBundle, PatientActivitiesBundle

admin.site.register(Activity)
admin.site.register(ClinicActivity)
admin.site.register(PatientActivity)
admin.site.register(ActivityReport)
admin.site.register(ActivitiesBundle)
admin.site.register(PatientActivitiesBundle)
