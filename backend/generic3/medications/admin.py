from django.contrib import admin
from .models import Medicines, ClinicMedicine, PatientMedicine , MedicationReport , MedicationsBundle , PatientMedicationsBundle

admin.site.register(Medicines)
admin.site.register(ClinicMedicine)
admin.site.register(PatientMedicine)
admin.site.register(MedicationReport)
admin.site.register(MedicationsBundle)
admin.site.register(PatientMedicationsBundle)


