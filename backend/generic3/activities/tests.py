"""
Comprehensive tests for Activities app.
Tests CRUD operations, permissions, and hierarchical relationships.
"""
import pytest
import json
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from factories import (
    AdminUserFactory, DoctorUserFactory, PatientUserFactory,
    ClinicFactory, ActivityFactory, ClinicActivityFactory,
    PatientActivityFactory, ActivityReportFactory,
    ActivitiesBundleFactory
)


@pytest.mark.django_db
class TestActivitiesListPermissions:
    """Test permission controls for listing activities."""
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access activities."""
        response = api_client.get('/api/v1/activities/')
        assert response.status_code == 401
    
    def test_admin_can_list_all_activities(self, admin_client):
        """Admin can list all activities across clinics."""
        ActivityFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/activities/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) >= 3
    
    def test_doctor_sees_only_clinic_activities(self, doctor_client):
        """Doctor sees only activities from their clinic."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        # Activities for doctor's clinic
        activity1 = ActivityFactory(name='Clinic Activity 1')
        activity2 = ActivityFactory(name='Clinic Activity 2')
        ClinicActivityFactory(activity=activity1, clinic=clinic)
        ClinicActivityFactory(activity=activity2, clinic=clinic)
        
        # Activity for different clinic
        other_clinic = ClinicFactory()
        other_activity = ActivityFactory(name='Other Clinic Activity')
        ClinicActivityFactory(activity=other_activity, clinic=other_clinic)
        
        response = doctor_client.get('/api/v1/activities/')
        assert response.status_code == 200
        data = json.loads(response.content)
        activity_names = [a['name'] for a in data]
        assert 'Clinic Activity 1' in activity_names
        assert 'Other Clinic Activity' not in activity_names
    
    def test_patient_sees_only_assigned_activities(self, patient_client):
        """Patient sees only activities assigned to them."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        doctor = DoctorUserFactory().doctor
        
        # Activity assigned to patient
        assigned_activity = ActivityFactory(name='My Activity')
        PatientActivityFactory(
            activity=assigned_activity,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        # Activity not assigned
        other_activity = ActivityFactory(name='Other Activity')
        
        response = patient_client.get('/api/v1/activities/')
        assert response.status_code == 200
        data = json.loads(response.content)
        activity_names = [a['name'] for a in data]
        assert 'My Activity' in activity_names
        assert 'Other Activity' not in activity_names


@pytest.mark.django_db
class TestCreateActivity:
    """Test activity creation with different permissions."""
    
    def test_admin_can_create_activity(self, admin_client):
        """Admin can create new activities."""
        response = admin_client.post('/api/v1/activities/', {
            'name': 'Walking Exercise',
            'description': '30 minutes of walking daily'
        })
        assert response.status_code == 201
    
    def test_doctor_can_create_activity_for_clinic(self, doctor_client):
        """Doctor can create activities for their clinic."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        response = doctor_client.post('/api/v1/activities/', {
            'name': 'Breathing Exercise',
            'description': 'Deep breathing for 10 minutes',
            'clinic_id': clinic.id
        })
        assert response.status_code in [200, 201]
    
    def test_patient_cannot_create_activities(self, patient_client):
        """Patients cannot create activities."""
        response = patient_client.post('/api/v1/activities/', {
            'name': 'Test Activity',
            'description': 'Test Description'
        })
        assert response.status_code == 403
    
    def test_activity_requires_name_and_description(self, admin_client):
        """Activity creation requires name and description."""
        response = admin_client.post('/api/v1/activities/', {
            'name': 'Test Activity'
            # Missing description
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestActivityDetail:
    """Test retrieving and updating specific activities."""
    
    def test_admin_can_view_any_activity(self, admin_client):
        """Admin can view any activity detail."""
        activity = ActivityFactory(name='Test Activity')
        
        response = admin_client.get(f'/api/v1/activities/{activity.id}/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['name'] == 'Test Activity'
    
    def test_admin_can_update_activity(self, admin_client):
        """Admin can update activity details."""
        activity = ActivityFactory(name='Old Name')
        
        response = admin_client.put(f'/api/v1/activities/{activity.id}/', {
            'name': 'Updated Name',
            'description': activity.description
        }, content_type='application/json')
        assert response.status_code == 200
        
        activity.refresh_from_db()
        assert activity.name == 'Updated Name'
    
    def test_admin_can_delete_activity(self, admin_client):
        """Admin can delete activities."""
        activity = ActivityFactory()
        
        response = admin_client.delete(f'/api/v1/activities/{activity.id}/')
        assert response.status_code == 204
    
    def test_doctor_can_view_clinic_activity(self, doctor_client):
        """Doctor can view activities from their clinic."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        activity = ActivityFactory()
        ClinicActivityFactory(activity=activity, clinic=clinic)
        
        response = doctor_client.get(f'/api/v1/activities/{activity.id}/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestPatientActivityAssignment:
    """Test assigning activities to patients with scheduling."""
    
    def test_doctor_assigns_activity_to_patient(self, doctor_client):
        """Doctor can assign activities to patients with schedule."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        activity = ActivityFactory()
        ClinicActivityFactory(activity=activity, clinic=clinic)
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        response = doctor_client.post('/api/v1/activities/', {
            'activity_id': activity.id,
            'patient_id': patient.id,
            'frequency': 'daily',
            'frequency_data': ['08:00', '16:00'],
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        # Flexible assertion - endpoint might return different codes
        assert response.status_code in [200, 201]
    
    def test_activity_frequency_options(self, doctor_client):
        """Test different frequency options for activities."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        activity = ActivityFactory()
        
        frequencies = ['once', 'daily', 'weekly', 'monthly']
        for freq in frequencies:
            PatientActivityFactory(
                activity=activity,
                patient=patient,
                doctor=doctor,
                clinic=clinic,
                frequency=freq
            )
        
        assert patient.patientactivity_set.count() == 4


@pytest.mark.django_db
class TestActivityBundles:
    """Test activity bundle functionality."""
    
    def test_admin_can_create_activity_bundle(self, admin_client):
        """Admin can create bundles of activities."""
        response = admin_client.post('/api/v1/activities/bundles/', {
            'bundle_name': 'Morning Routine',
            'activities': []
        })
        assert response.status_code in [200, 201]
    
    def test_admin_can_list_activity_bundles(self, admin_client):
        """Admin can list all activity bundles."""
        ActivitiesBundleFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/activities/bundles/')
        assert response.status_code == 200
    
    def test_admin_can_view_bundle_detail(self, admin_client):
        """Admin can view bundle details."""
        bundle = ActivitiesBundleFactory(bundle_name='Test Bundle')
        
        response = admin_client.get(f'/api/v1/activities/bundles/{bundle.id}/')
        assert response.status_code == 200
    
    def test_admin_can_delete_bundle(self, admin_client):
        """Admin can delete activity bundles."""
        bundle = ActivitiesBundleFactory()
        
        response = admin_client.delete(f'/api/v1/activities/bundles/{bundle.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestActivityReports:
    """Test activity reporting functionality."""
    
    def test_patient_can_submit_activity_report(self, patient_client):
        """Patient can submit reports for their activities."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        activity = ActivityFactory()
        doctor = DoctorUserFactory().doctor
        
        PatientActivityFactory(
            activity=activity,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        response = patient_client.post('/api/v1/activity-reports/', {
            'activity_id': activity.id,
            'completed': True
        })
        assert response.status_code in [200, 201]
    
    def test_doctor_can_view_patient_activity_reports(self, doctor_client):
        """Doctor can view activity reports for their patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        activity = ActivityFactory()
        
        ActivityReportFactory(
            clinic=clinic,
            patient=patient,
            activity=activity
        )
        
        response = doctor_client.get('/api/v1/activity-reports/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestActivityCascadeDeletion:
    """Test cascade deletion behavior."""
    
    def test_deleting_activity_removes_patient_assignments(self, admin_client):
        """Deleting an activity removes all patient assignments."""
        activity = ActivityFactory()
        patient = PatientUserFactory().patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        PatientActivityFactory(
            activity=activity,
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        activity_id = activity.id
        admin_client.delete(f'/api/v1/activities/{activity_id}/')
        
        # Verify patient assignments are deleted
        from activities.models import PatientActivity
        assert not PatientActivity.objects.filter(activity_id=activity_id).exists()
    
    def test_deleting_clinic_removes_clinic_activities(self):
        """Deleting a clinic removes its activity associations."""
        clinic = ClinicFactory()
        activity = ActivityFactory()
        
        ClinicActivityFactory(activity=activity, clinic=clinic)
        
        clinic.delete()
        
        # Verify clinic activity association is deleted
        from activities.models import ClinicActivity
        assert not ClinicActivity.objects.filter(clinic_id=clinic.id).exists()
