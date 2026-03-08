from django.utils import timezone
from django.db import models
from users.models import Doctor, Patient
from clinics.models import Clinic

medicinesRepeatPeriods = (
    ('once','once'),
    ('daily','daily'),
    ('weekly','weekly'),
    ('monthly','monthly'),
)

class Medicines(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    medForm = models.CharField(max_length=255)
    medName = models.CharField(max_length=255)
    medUnitOfMeasurement = models.CharField(max_length=255)
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Get the last ID and increment, or start at 1000000000
            last_medicine = Medicines.objects.order_by('-id').first()
            if last_medicine:
                self.id = int(last_medicine.id) + 1
            else:
                self.id = 1000000000
        super().save(*args, **kwargs)

class ClinicMedicine(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE , related_name='clinic_id')
    medicine = models.ForeignKey(Medicines, on_delete= models.CASCADE)

class PatientMedicine(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
    )
    medicine = models.ForeignKey(
        Medicines,
        on_delete=models.CASCADE,
    )

    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        null=True, blank=True,         
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        null=True, blank=True,
    )

    frequency       = models.CharField(max_length=30,
                                       choices=medicinesRepeatPeriods,
                                       default='once',)
    frequency_data  = models.JSONField(default=list, null=True, blank=True)
    start_date      = models.DateTimeField(default=timezone.now)
    end_date        = models.DateTimeField(default=timezone.datetime(2100, 1, 1))
    dosage          = models.CharField(max_length=255, null=True, blank=True)


class MedicationReport(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    medication = models.ForeignKey(Medicines, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    

class MedicationsBundle(models.Model):
    bundle_name = models.CharField(max_length=255)
    medicines = models.ManyToManyField(Medicines , related_name='bundled_medicines') 
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    
class PatientMedicationsBundle(models.Model): 
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE , related_name="patient_medication_bundles")
    bundle = models.ForeignKey(MedicationsBundle, on_delete=models.CASCADE , related_name="patient_medication_bundles")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE , related_name="doctor_medication_bundles")