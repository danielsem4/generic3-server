"""
Comprehensive tests for Notifications app.
Tests event notification settings and scheduling.
"""
import pytest
import json
from django.utils import timezone
from datetime import timedelta
from factories import (
    AdminUserFactory, DoctorUserFactory, PatientUserFactory,
    ClinicFactory, EventNotificationSettingsFactory,
    ActivityFactory, MedicinesFactory
)


@pytest.mark.django_db
class TestNotificationSettingsPermissions:
    """Test permission controls for notification settings."""
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access notification settings."""
        response = api_client.post('/api/v1/notifications/set/notification/', {})
        assert response.status_code == 401
    
    def test_patient_can_set_own_notifications(self, patient_client):
        """Patient can set notification settings for themselves."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        activity = ActivityFactory()
        
        response = patient_client.post('/api/v1/notifications/set/notification/', {
            'clinic_id': clinic.id,
            'event_type': 'activity',
            'event_id': activity.id,
            'frequency': 'daily',
            'frequency_data': ['08:00', '20:00']
        })
        assert response.status_code in [200, 201]
    
    def test_doctor_can_set_patient_notifications(self, doctor_client):
        """Doctor can set notification settings for their patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        medicine = MedicinesFactory()
        
        response = doctor_client.post('/api/v1/notifications/set/notification/', {
            'patient_id': patient.id,
            'clinic_id': clinic.id,
            'event_type': 'medication',
            'event_id': medicine.id,
            'frequency': 'daily',
            'frequency_data': ['09:00', '21:00']
        })
        assert response.status_code in [200, 201]


@pytest.mark.django_db
class TestNotificationEventTypes:
    """Test different event types for notifications."""
    
    def test_medication_notification_settings(self):
        """Test creating notification settings for medication events."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        medicine = MedicinesFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=int(medicine.id),
            frequency='daily',
            frequency_data=['08:00', '14:00', '20:00']
        )
        
        assert notification.event_type == 'medication'
        assert notification.frequency == 'daily'
        assert len(notification.frequency_data) == 3
    
    def test_activity_notification_settings(self):
        """Test creating notification settings for activity events."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        activity = ActivityFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=activity.id,
            frequency='weekly',
            frequency_data=['Monday', 'Wednesday', 'Friday']
        )
        
        assert notification.event_type == 'activity'
        assert notification.frequency == 'weekly'
    
    def test_questionnaire_notification_settings(self):
        """Test creating notification settings for questionnaire events."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='questionnaire',
            event_id=1,
            frequency='monthly',
            frequency_data=['1', '15']  # 1st and 15th of month
        )
        
        assert notification.event_type == 'questionnaire'
        assert notification.frequency == 'monthly'


@pytest.mark.django_db
class TestNotificationFrequency:
    """Test different frequency options for notifications."""
    
    def test_once_frequency(self):
        """Test notification with 'once' frequency."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='once',
            frequency_data=[],
            start_date_time=timezone.now()
        )
        
        assert notification.frequency == 'once'
    
    def test_daily_frequency(self):
        """Test notification with 'daily' frequency."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1,
            frequency='daily',
            frequency_data=['06:00', '12:00', '18:00']
        )
        
        assert notification.frequency == 'daily'
        assert len(notification.frequency_data) == 3
    
    def test_weekly_frequency(self):
        """Test notification with 'weekly' frequency."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='weekly',
            frequency_data=['Monday', 'Thursday', 'Saturday']
        )
        
        assert notification.frequency == 'weekly'
    
    def test_monthly_frequency(self):
        """Test notification with 'monthly' frequency."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1,
            frequency='monthly',
            frequency_data=['1', '10', '20']
        )
        
        assert notification.frequency == 'monthly'


@pytest.mark.django_db
class TestNotificationScheduling:
    """Test notification scheduling with start and end dates."""
    
    def test_notification_with_start_date(self):
        """Test notification with specified start date."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        start_date = timezone.now() + timedelta(days=1)
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='daily',
            start_date_time=start_date
        )
        
        assert notification.start_date_time == start_date
    
    def test_notification_with_end_date(self):
        """Test notification with specified end date."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='daily',
            start_date_time=start_date,
            end_date_time=end_date
        )
        
        assert notification.end_date_time == end_date
    
    def test_notification_without_end_date(self):
        """Test notification without end date (indefinite)."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1,
            frequency='daily',
            end_date_time=None
        )
        
        assert notification.end_date_time is None


@pytest.mark.django_db
class TestNotificationDataIntegrity:
    """Test data integrity and validation."""
    
    def test_notification_can_be_patient_specific(self):
        """Test patient-specific notification settings."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1
        )
        
        assert notification.patient == patient
        assert notification.clinic == clinic
    
    def test_notification_can_be_clinic_wide(self):
        """Test clinic-wide notification settings (no specific patient)."""
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            clinic=clinic,
            patient=None,
            event_type='activity',
            event_id=1
        )
        
        assert notification.clinic == clinic
        assert notification.patient is None
    
    def test_notification_stores_frequency_data_as_json(self):
        """Test that frequency_data is stored as JSON."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        time_slots = ['08:00', '12:00', '16:00', '20:00']
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='daily',
            frequency_data=time_slots
        )
        
        assert notification.frequency_data == time_slots
        assert isinstance(notification.frequency_data, list)
    
    def test_multiple_notifications_for_same_patient(self):
        """Test that a patient can have multiple notification settings."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        # Notification for medication
        EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='daily'
        )
        
        # Notification for activity
        EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1,
            frequency='weekly'
        )
        
        # Notification for questionnaire
        EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='questionnaire',
            event_id=1,
            frequency='monthly'
        )
        
        from notifications.models import EventNotificationSettings
        assert EventNotificationSettings.objects.filter(patient=patient).count() == 3


@pytest.mark.django_db
class TestNotificationCascadeDeletion:
    """Test cascade deletion behavior."""
    
    def test_deleting_patient_removes_notifications(self):
        """Deleting a patient removes all their notification settings."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1
        )
        
        patient_id = patient.id
        patient.delete()
        
        # Verify notification settings are deleted
        from notifications.models import EventNotificationSettings
        assert not EventNotificationSettings.objects.filter(patient_id=patient_id).exists()
    
    def test_deleting_clinic_removes_notifications(self):
        """Deleting a clinic removes all associated notification settings."""
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1
        )
        
        clinic_id = clinic.id
        clinic.delete()
        
        # Verify notification settings are deleted
        from notifications.models import EventNotificationSettings
        assert not EventNotificationSettings.objects.filter(clinic_id=clinic_id).exists()


@pytest.mark.django_db
class TestNotificationUpdate:
    """Test updating notification settings."""
    
    def test_patient_can_update_notification_frequency(self, patient_client):
        """Patient can update their notification frequency."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='medication',
            event_id=1,
            frequency='daily',
            frequency_data=['08:00']
        )
        
        # Update frequency_data
        notification.frequency_data = ['08:00', '20:00']
        notification.save()
        
        notification.refresh_from_db()
        assert len(notification.frequency_data) == 2
    
    def test_doctor_can_update_patient_notification_schedule(self):
        """Doctor can update patient notification schedule."""
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        patient = PatientUserFactory().patient
        
        notification = EventNotificationSettingsFactory(
            patient=patient,
            clinic=clinic,
            event_type='activity',
            event_id=1,
            frequency='weekly'
        )
        
        # Update to daily
        notification.frequency = 'daily'
        notification.frequency_data = ['09:00', '17:00']
        notification.save()
        
        notification.refresh_from_db()
        assert notification.frequency == 'daily'
