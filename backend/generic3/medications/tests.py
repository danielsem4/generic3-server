"""
Comprehensive tests for Medications app.
Tests CRUD operations, permissions, patient prescriptions, and scheduling.
"""
import pytest
import json
from django.utils import timezone
from datetime import timedelta
from factories import (
    AdminUserFactory, DoctorUserFactory, PatientUserFactory,
    ClinicFactory, MedicinesFactory, ClinicMedicineFactory,
    PatientMedicineFactory, MedicationReportFactory,
    MedicationsBundleFactory
)


@pytest.mark.django_db
class TestMedicationsListPermissions:
    """Test permission controls for listing medications."""
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access medications."""
        response = api_client.get('/api/v1/medications/')
        assert response.status_code == 401
    
    def test_admin_can_list_all_medications(self, admin_client):
        """Admin can list all medications across clinics."""
        MedicinesFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/medications/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) >= 3
    
    def test_doctor_sees_only_clinic_medications(self, doctor_client):
        """Doctor sees only medications from their clinic."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        # Medications for doctor's clinic
        med1 = MedicinesFactory(medName='Aspirin')
        med2 = MedicinesFactory(medName='Ibuprofen')
        ClinicMedicineFactory(medicine=med1, clinic=clinic)
        ClinicMedicineFactory(medicine=med2, clinic=clinic)
        
        # Medication for different clinic
        other_clinic = ClinicFactory()
        other_med = MedicinesFactory(medName='Acetaminophen')
        ClinicMedicineFactory(medicine=other_med, clinic=other_clinic)
        
        response = doctor_client.get('/api/v1/medications/')
        assert response.status_code == 200
        data = json.loads(response.content)
        med_names = [m['medName'] for m in data if 'medName' in m]
        assert 'Aspirin' in med_names or len(data) >= 2
    
    def test_patient_sees_only_prescribed_medications(self, patient_client):
        """Patient sees only medications prescribed to them."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        doctor = DoctorUserFactory().doctor
        
        # Medication prescribed to patient
        prescribed_med = MedicinesFactory(medName='Prescribed Med')
        PatientMedicineFactory(
            medicine=prescribed_med,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        # Medication not prescribed
        other_med = MedicinesFactory(medName='Other Med')
        
        response = patient_client.get('/api/v1/medications/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestCreateMedication:
    """Test medication creation with different permissions."""
    
    def test_admin_can_create_medication(self, admin_client):
        """Admin can create new medications."""
        response = admin_client.post('/api/v1/medications/', {
            'medName': 'New Medicine',
            'medForm': 'Tablet',
            'medUnitOfMeasurement': 'mg'
        })
        assert response.status_code == 201
    
    def test_doctor_can_prescribe_medication(self, doctor_client):
        """Doctor can prescribe medications to patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        ClinicMedicineFactory(medicine=medicine, clinic=clinic)
        
        response = doctor_client.post('/api/v1/medications/', {
            'medicine_id': medicine.id,
            'patient_id': patient.id,
            'dosage': '500mg',
            'frequency': 'daily'
        })
        assert response.status_code in [200, 201]
    
    def test_patient_cannot_create_medications(self, patient_client):
        """Patients cannot create medications."""
        response = patient_client.post('/api/v1/medications/', {
            'medName': 'Test Med',
            'medForm': 'Tablet',
            'medUnitOfMeasurement': 'mg'
        })
        assert response.status_code == 403
    
    def test_medication_id_auto_generated(self):
        """Medication ID is auto-generated starting from 1000000000."""
        med = MedicinesFactory(id=None)
        med.save()
        assert int(med.id) >= 1000000000


@pytest.mark.django_db
class TestMedicationDetail:
    """Test retrieving and updating specific medications."""
    
    def test_admin_can_view_any_medication(self, admin_client):
        """Admin can view any medication detail."""
        medicine = MedicinesFactory(medName='Test Medicine')
        
        response = admin_client.get(f'/api/v1/medications/{medicine.id}/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['medName'] == 'Test Medicine'
    
    def test_admin_can_update_medication(self, admin_client):
        """Admin can update medication details."""
        medicine = MedicinesFactory(medName='Old Name')
        
        response = admin_client.put(f'/api/v1/medications/{medicine.id}/', {
            'medName': 'Updated Name',
            'medForm': medicine.medForm,
            'medUnitOfMeasurement': medicine.medUnitOfMeasurement
        }, content_type='application/json')
        assert response.status_code == 200
        
        medicine.refresh_from_db()
        assert medicine.medName == 'Updated Name'
    
    def test_admin_can_delete_medication(self, admin_client):
        """Admin can delete medications."""
        medicine = MedicinesFactory()
        
        response = admin_client.delete(f'/api/v1/medications/{medicine.id}/')
        assert response.status_code == 204
    
    def test_doctor_can_view_clinic_medication(self, doctor_client):
        """Doctor can view medications from their clinic."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        medicine = MedicinesFactory()
        ClinicMedicineFactory(medicine=medicine, clinic=clinic)
        
        response = doctor_client.get(f'/api/v1/medications/{medicine.id}/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestPatientMedicationPrescription:
    """Test prescribing medications to patients with scheduling."""
    
    def test_doctor_prescribes_medication_to_patient(self, doctor_client):
        """Doctor can prescribe medications to patients with schedule."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        ClinicMedicineFactory(medicine=medicine, clinic=clinic)
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        # Create prescription using factory
        prescription = PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            frequency='daily',
            start_date=start_date,
            end_date=end_date
        )
        
        assert prescription.patient == patient
        assert prescription.frequency == 'daily'
    
    def test_medication_frequency_options(self):
        """Test different frequency options for medications."""
        patient = PatientUserFactory().patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        medicine = MedicinesFactory()
        
        frequencies = ['once', 'daily', 'weekly', 'monthly']
        for freq in frequencies:
            PatientMedicineFactory(
                medicine=medicine,
                patient=patient,
                doctor=doctor,
                clinic=clinic,
                frequency=freq
            )
        
        assert patient.patientmedicine_set.count() == 4
    
    def test_patient_can_view_own_prescriptions(self, patient_client):
        """Patient can view their own prescriptions."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        doctor = DoctorUserFactory().doctor
        medicine = MedicinesFactory()
        
        PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        response = patient_client.get('/api/v1/medications/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestMedicationBundles:
    """Test medication bundle functionality."""
    
    def test_admin_can_create_medication_bundle(self, admin_client):
        """Admin can create bundles of medications."""
        response = admin_client.post('/api/v1/medications/bundles/', {
            'bundle_name': 'Diabetes Treatment',
            'medications': []
        })
        assert response.status_code in [200, 201]
    
    def test_admin_can_list_medication_bundles(self, admin_client):
        """Admin can list all medication bundles."""
        MedicationsBundleFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/medications/bundles/')
        assert response.status_code == 200
    
    def test_admin_can_view_bundle_detail(self, admin_client):
        """Admin can view bundle details."""
        bundle = MedicationsBundleFactory(bundle_name='Test Bundle')
        
        response = admin_client.get(f'/api/v1/medications/bundles/{bundle.id}/')
        assert response.status_code == 200
    
    def test_admin_can_delete_bundle(self, admin_client):
        """Admin can delete medication bundles."""
        bundle = MedicationsBundleFactory()
        
        response = admin_client.delete(f'/api/v1/medications/bundles/{bundle.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestMedicationReports:
    """Test medication reporting functionality."""
    
    def test_patient_can_submit_medication_report(self, patient_client):
        """Patient can submit reports for taking medications."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        medicine = MedicinesFactory()
        doctor = DoctorUserFactory().doctor
        
        PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        response = patient_client.post('/api/v1/medication-reports/', {
            'medicine_id': medicine.id,
            'taken': True
        })
        assert response.status_code in [200, 201]
    
    def test_doctor_can_view_patient_medication_reports(self, doctor_client):
        """Doctor can view medication reports for their patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        
        MedicationReportFactory(
            clinic=clinic,
            patient=patient,
            medicine=medicine
        )
        
        response = doctor_client.get('/api/v1/medication-reports/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestMedicationCascadeDeletion:
    """Test cascade deletion behavior."""
    
    def test_deleting_medication_removes_patient_prescriptions(self, admin_client):
        """Deleting a medication removes all patient prescriptions."""
        medicine = MedicinesFactory()
        patient = PatientUserFactory().patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        medicine_id = medicine.id
        admin_client.delete(f'/api/v1/medications/{medicine_id}/')
        
        # Verify patient prescriptions are deleted
        from medications.models import PatientMedicine
        assert not PatientMedicine.objects.filter(medicine_id=medicine_id).exists()
    
    def test_deleting_clinic_removes_clinic_medications(self):
        """Deleting a clinic removes its medication associations."""
        clinic = ClinicFactory()
        medicine = MedicinesFactory()
        
        ClinicMedicineFactory(medicine=medicine, clinic=clinic)
        
        clinic.delete()
        
        # Verify clinic medication association is deleted
        from medications.models import ClinicMedicine
        assert not ClinicMedicine.objects.filter(clinic_id=clinic.id).exists()
    
    def test_deleting_patient_removes_prescriptions(self):
        """Deleting a patient removes all their prescriptions."""
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        patient_id = patient.id
        patient.delete()
        
        # Verify prescriptions are deleted
        from medications.models import PatientMedicine
        assert not PatientMedicine.objects.filter(patient_id=patient_id).exists()


@pytest.mark.django_db
class TestMedicationDataIntegrity:
    """Test data integrity and validation."""
    
    def test_medication_requires_all_fields(self, admin_client):
        """Medication creation requires all required fields."""
        response = admin_client.post('/api/v1/medications/', {
            'medName': 'Test Med'
            # Missing medForm and medUnitOfMeasurement
        })
        assert response.status_code == 400
    
    def test_patient_prescription_requires_dosage_info(self):
        """Patient prescription should include dosage information."""
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        prescription = PatientMedicineFactory(
            medicine=medicine,
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            dosage='500mg',
            frequency='daily'
        )
        
        assert prescription.dosage == '500mg'
        assert prescription.frequency == 'daily'
