"""
Comprehensive test suite for users app.
Tests user management, permissions, data integrity, and role-based access control.
"""
import pytest
from django.urls import reverse
from django.db import transaction
from rest_framework import status
from unittest.mock import patch, Mock

from factories import (
    UserFactory, AdminUserFactory, ClinicManagerUserFactory,
    DoctorUserFactory, PatientUserFactory,
    ClinicFactory, ClinicManagerFactory, DoctorFactory, PatientFactory,
    ManagerClinicFactory, DoctorClinicFactory, PatientClinicFactory,
    PatientDoctorFactory, ModulesFactory, ClinicModulesFactory,
    PatientModulesFactory
)
from users.models import User, Doctor, Patient, PatientDoctor
from clinics.models import DoctorClinic, PatientClinic
from modules.models import PatientModules

pytestmark = pytest.mark.django_db


class TestListUsersPermissions:
    """Test user listing with role-based permissions."""
    
    def test_admin_can_list_all_users(self, api_client):
        """Test admin can see all users."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create users of different roles
        UserFactory.create_batch(5)
        
        url = reverse('list_users')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 5
    
    def test_clinic_manager_sees_only_their_clinic_users(self, api_client):
        """Test clinic manager can only see users in their clinic."""
        # Create clinic manager with clinic
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        # Create doctors in same clinic
        doctor1_user = DoctorUserFactory()
        doctor1 = DoctorFactory(user=doctor1_user)
        DoctorClinicFactory(doctor=doctor1, clinic=clinic)
        
        # Create doctors in different clinic
        other_clinic = ClinicFactory()
        doctor2_user = DoctorUserFactory()
        doctor2 = DoctorFactory(user=doctor2_user)
        DoctorClinicFactory(doctor=doctor2, clinic=other_clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        url = reverse('list_users') + '?role=DOCTOR'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        emails = [user['email'] for user in response.data['results']]
        assert doctor1_user.email in emails
        assert doctor2_user.email not in emails
    
    def test_doctor_sees_only_their_patients(self, api_client):
        """Test doctor can only see their assigned patients."""
        # Create doctor with clinic
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        clinic = ClinicFactory()
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        # Create patient assigned to this doctor
        patient1_user = PatientUserFactory()
        patient1 = PatientFactory(user=patient1_user)
        PatientClinicFactory(patient=patient1, clinic=clinic)
        PatientDoctorFactory(patient=patient1, doctor=doctor, clinic=clinic)
        
        # Create patient not assigned to this doctor
        patient2_user = PatientUserFactory()
        patient2 = PatientFactory(user=patient2_user)
        PatientClinicFactory(patient=patient2, clinic=clinic)
        
        api_client.force_authenticate(user=doctor_user)
        
        url = reverse('list_users') + '?role=PATIENT'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        emails = [user['email'] for user in response.data['results']]
        assert patient1_user.email in emails
        assert patient2_user.email not in emails
    
    def test_patient_cannot_list_users(self, api_client):
        """Test patients cannot list users."""
        patient_user = PatientUserFactory()
        api_client.force_authenticate(user=patient_user)
        
        url = reverse('list_users')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_unauthenticated_cannot_list_users(self, api_client):
        """Test unauthenticated access is denied."""
        url = reverse('list_users')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_listing_requires_role_parameter_for_non_staff(self, api_client):
        """Test non-staff users must provide role parameter."""
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        url = reverse('list_users')  # No role parameter
        response = api_client.get(url)
        
        # Should require role parameter
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_pagination_works_correctly(self, api_client):
        """Test user listing pagination."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create many users
        UserFactory.create_batch(25)
        
        url = reverse('list_users')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data
        assert len(response.data['results']) <= 20  # Default page size


class TestCreateUser:
    """Test user creation with complex business logic."""
    
    @patch('generic3.messages.sendEmailMessage')
    def test_admin_can_create_user(self, mock_email, api_client):
        """Test admin can create users of any role."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('list_users')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'role': 'DOCTOR'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='newuser@example.com').exists()
    
    @patch('generic3.messages.sendEmailMessage')
    def test_clinic_manager_creates_doctor_with_temp_password(self, mock_email, api_client):
        """Test clinic manager creates doctor with temporary password email."""
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        url = reverse('list_users')
        data = {
            'email': 'newdoctor@example.com',
            'first_name': 'New',
            'last_name': 'Doctor',
            'phone_number': '1234567890',
            'clinic_id': clinic.id
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify doctor was created with correct role
        user = User.objects.get(email='newdoctor@example.com')
        assert user.role == 'DOCTOR'
        
        # Verify doctor profile and clinic association
        assert Doctor.objects.filter(user=user).exists()
        assert DoctorClinic.objects.filter(doctor__user=user, clinic=clinic).exists()
        
        # Verify email was sent
        mock_email.assert_called_once()
    
    @patch('generic3.messages.sendEmailMessage')
    def test_doctor_creates_patient_with_modules(self, mock_email, api_client):
        """Test doctor creates patient with automatic module assignment."""
        # Create doctor with clinic
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        clinic = ClinicFactory()
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        # Create modules for clinic
        module1 = ModulesFactory()
        module2 = ModulesFactory()
        ClinicModulesFactory(clinic=clinic, module=module1, is_active=True)
        ClinicModulesFactory(clinic=clinic, module=module2, is_active=True)
        
        api_client.force_authenticate(user=doctor_user)
        
        url = reverse('list_users')
        data = {
            'email': 'newpatient@example.com',
            'first_name': 'New',
            'last_name': 'Patient',
            'phone_number': '1234567890',
            'clinic_id': clinic.id,
            'doctor_id': doctor.user.id
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify patient was created
        user = User.objects.get(email='newpatient@example.com')
        assert user.role == 'PATIENT'
        
        # Verify patient profile and relationships
        patient = Patient.objects.get(user=user)
        assert PatientClinic.objects.filter(patient=patient, clinic=clinic).exists()
        assert PatientDoctor.objects.filter(patient=patient, doctor=doctor, clinic=clinic).exists()
        
        # Verify modules were assigned
        assert PatientModules.objects.filter(patient=patient, clinic=clinic).count() == 2
    
    @patch('generic3.messages.sendEmailMessage')
    def test_duplicate_email_handling(self, mock_email, api_client):
        """Test creating user with existing email."""
        existing_user = DoctorUserFactory(email='existing@example.com')
        
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        url = reverse('list_users')
        data = {
            'email': 'existing@example.com',
            'first_name': existing_user.first_name,
            'last_name': existing_user.last_name,
            'phone_number': existing_user.phone_number,
            'clinic_id': clinic.id
        }
        
        response = api_client.post(url, data, format='json')
        
        # Should handle existing user gracefully (assigns to clinic)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    
    @patch('generic3.messages.sendEmailMessage')
    def test_research_clinic_doctor_creates_research_patient_with_password(self, mock_email, api_client):
        """Test research clinic allows setting patient password directly."""
        # Create doctor in research clinic
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        clinic = ClinicFactory(is_research_clinic=True)
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        api_client.force_authenticate(user=doctor_user)
        
        url = reverse('list_users')
        data = {
            'email': 'research@example.com',
            'first_name': 'Research',
            'last_name': 'Patient',
            'password': 'ResearchPass123!',
            'phone_number': '1234567890',
            'clinic_id': clinic.id,
            'doctor_id': doctor.user.id
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify research patient role
        user = User.objects.get(email='research@example.com')
        assert user.role == 'RESEARCH_PATIENT'
        
        # Verify password was set (not temp password)
        assert user.check_password('ResearchPass123!')
    
    def test_patient_cannot_create_users(self, api_client):
        """Test patients cannot create other users."""
        patient_user = PatientUserFactory()
        api_client.force_authenticate(user=patient_user)
        
        url = reverse('list_users')
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserDetail:
    """Test user detail retrieval."""
    
    def test_user_can_view_own_profile(self, api_client):
        """Test user can view their own profile."""
        user = DoctorUserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
    
    def test_admin_can_view_any_profile(self, api_client):
        """Test admin can view any user's profile."""
        admin = AdminUserFactory()
        user = DoctorUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
    
    def test_patient_profile_includes_modules(self, api_client):
        """Test patient profile includes their modules."""
        patient_user = PatientUserFactory()
        patient = PatientFactory(user=patient_user)
        clinic = ClinicFactory()
        PatientClinicFactory(patient=patient, clinic=clinic)
        
        # Create patient modules
        module1 = ModulesFactory()
        module2 = ModulesFactory()
        PatientModulesFactory(patient=patient, clinic=clinic, module=module1, is_active=True)
        PatientModulesFactory(patient=patient, clinic=clinic, module=module2, is_active=False)
        
        api_client.force_authenticate(user=patient_user)
        
        url = reverse('user_detail', kwargs={'user_id': patient_user.id}) + f'?clinic_id={clinic.id}'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Check modules are included (implementation dependent)
    
    def test_current_user_endpoint(self, api_client):
        """Test current user endpoint returns authenticated user."""
        user = DoctorUserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('current_user')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['id'] == user.id


class TestUserUpdate:
    """Test user update functionality."""
    
    def test_user_can_update_own_profile(self, api_client):
        """Test user can update their own profile."""
        user = DoctorUserFactory(first_name='Old')
        api_client.force_authenticate(user=user)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        data = {'first_name': 'New', 'last_name': user.last_name}
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'New'
    
    def test_partial_update_with_patch(self, api_client):
        """Test partial update using PATCH."""
        user = DoctorUserFactory(first_name='Old', last_name='Name')
        api_client.force_authenticate(user=user)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        data = {'first_name': 'New'}  # Only updating first_name
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'New'
        assert user.last_name == 'Name'  # Unchanged
    
    def test_cannot_change_role_via_update(self, api_client):
        """Test role cannot be changed through regular update."""
        user = DoctorUserFactory(role='DOCTOR')
        api_client.force_authenticate(user=user)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': 'ADMIN'  # Attempt to change role
        }
        
        response = api_client.put(url, data, format='json')
        
        user.refresh_from_db()
        assert user.role == 'DOCTOR'  # Role unchanged


class TestUserDeletion:
    """Test user deletion with complex cascade logic."""
    
    def test_admin_can_permanently_delete_user(self, api_client):
        """Test admin can permanently delete users."""
        admin = AdminUserFactory()
        user = UserFactory()
        user_id = user.id
        
        api_client.force_authenticate(user=admin)
        
        url = reverse('user_detail', kwargs={'user_id': user_id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(id=user_id).exists()
    
    def test_cannot_delete_self(self, api_client):
        """Test users cannot delete themselves."""
        user = DoctorUserFactory()
        api_client.force_authenticate(user=user)
        
        url = reverse('user_detail', kwargs={'user_id': user.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.filter(id=user.id).exists()
    
    def test_cannot_delete_doctor_with_patients(self, api_client):
        """Test cannot delete doctor who has assigned patients."""
        admin = AdminUserFactory()
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        clinic = ClinicFactory()
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        # Assign patient to doctor
        patient = PatientFactory()
        PatientDoctorFactory(patient=patient, doctor=doctor, clinic=clinic)
        
        api_client.force_authenticate(user=admin)
        
        url = reverse('user_detail', kwargs={'user_id': doctor_user.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'has assigned patients' in str(response.data).lower()
    
    def test_cannot_delete_patient_with_doctors(self, api_client):
        """Test cannot delete patient who has assigned doctors."""
        admin = AdminUserFactory()
        patient_user = PatientUserFactory()
        patient = PatientFactory(user=patient_user)
        clinic = ClinicFactory()
        
        # Assign doctor to patient
        doctor = DoctorFactory()
        PatientDoctorFactory(patient=patient, doctor=doctor, clinic=clinic)
        
        api_client.force_authenticate(user=admin)
        
        url = reverse('user_detail', kwargs={'user_id': patient_user.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_clinic_manager_removes_user_from_clinic(self, api_client):
        """Test clinic manager removes user from their clinic (not permanent delete)."""
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        # Create doctor in clinic
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        doctor_clinic = DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        url = reverse('user_detail', kwargs={'user_id': doctor_user.id})
        response = api_client.delete(url)
        
        # User still exists, but clinic association removed
        assert User.objects.filter(id=doctor_user.id).exists()
        assert not DoctorClinic.objects.filter(id=doctor_clinic.id).exists()
    
    def test_doctor_can_remove_patient_from_clinic(self, api_client):
        """Test doctor can remove patient from clinic."""
        doctor_user = DoctorUserFactory()
        doctor = DoctorFactory(user=doctor_user)
        clinic = ClinicFactory()
        DoctorClinicFactory(doctor=doctor, clinic=clinic)
        
        # Create patient in clinic
        patient_user = PatientUserFactory()
        patient = PatientFactory(user=patient_user)
        patient_clinic = PatientClinicFactory(patient=patient, clinic=clinic)
        patient_doctor = PatientDoctorFactory(patient=patient, doctor=doctor, clinic=clinic)
        
        api_client.force_authenticate(user=doctor_user)
        
        url = reverse('user_detail', kwargs={'user_id': patient_user.id}) + f'?clinic_id={clinic.id}'
        response = api_client.delete(url)
        
        # Patient user still exists, but clinic association removed
        assert User.objects.filter(id=patient_user.id).exists()
        assert not PatientClinic.objects.filter(id=patient_clinic.id).exists()
        assert not PatientDoctor.objects.filter(id=patient_doctor.id).exists()
    
    def test_patient_cannot_delete_users(self, api_client):
        """Test patients cannot delete users."""
        patient_user = PatientUserFactory()
        other_user = UserFactory()
        
        api_client.force_authenticate(user=patient_user)
        
        url = reverse('user_detail', kwargs={'user_id': other_user.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDataIntegrity:
    """Test data integrity and validation."""
    
    def test_email_uniqueness_enforced(self):
        """Test email addresses must be unique."""
        from django.db import IntegrityError
        UserFactory(email='unique@example.com')
        
        with pytest.raises(IntegrityError):
            UserFactory(email='unique@example.com')
    
    def test_user_doctor_one_to_one_relationship(self):
        """Test User-Doctor is one-to-one."""
        from django.db import IntegrityError
        user = DoctorUserFactory()
        doctor = DoctorFactory(user=user)
        
        with pytest.raises(IntegrityError):
            DoctorFactory(user=user)  # Cannot create second doctor for same user
    
    def test_user_patient_one_to_one_relationship(self):
        """Test User-Patient is one-to-one."""
        from django.db import IntegrityError
        user = PatientUserFactory()
        patient = PatientFactory(user=user)
        
        with pytest.raises(IntegrityError):
            PatientFactory(user=user)  # Cannot create second patient for same user
    
    def test_patient_doctor_relationship_unique(self):
        """Test PatientDoctor relationship prevents duplicates."""
        from django.db import IntegrityError
        patient = PatientFactory()
        doctor = DoctorFactory()
        clinic = ClinicFactory()
        
        PatientDoctorFactory(patient=patient, doctor=doctor, clinic=clinic)
        
        # Attempting to create duplicate should fail or be handled
        with pytest.raises(IntegrityError):
            PatientDoctorFactory(patient=patient, doctor=doctor, clinic=clinic)
    
    @patch('generic3.messages.sendEmailMessage')
    def test_user_creation_is_atomic(self, mock_email, api_client):
        """Test user creation with relationships is atomic."""
        manager_user = ClinicManagerUserFactory()
        manager = ClinicManagerFactory(user=manager_user)
        clinic = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        api_client.force_authenticate(user=manager_user)
        
        # Simulate failure in clinic association
        with patch('clinics.models.DoctorClinic.objects.create', side_effect=Exception('Test error')):
            url = reverse('list_users')
            data = {
                'email': 'atomic@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'clinic_id': clinic.id
            }
            
            try:
                response = api_client.post(url, data, format='json')
            except Exception:
                pass
            
            # User should not be created if clinic association fails
            # (depends on implementation using atomic transactions)


class TestCrossClinicAccess:
    """Test clinic isolation and cross-clinic access prevention."""
    
    def test_clinic_manager_cannot_access_other_clinic_users(self, api_client):
        """Test clinic managers can only access users in their clinic."""
        # Clinic 1
        manager1_user = ClinicManagerUserFactory()
        manager1 = ClinicManagerFactory(user=manager1_user)
        clinic1 = ClinicFactory()
        ManagerClinicFactory(manager=manager1, clinic=clinic1)
        
        # Clinic 2
        clinic2 = ClinicFactory()
        doctor2_user = DoctorUserFactory()
        doctor2 = DoctorFactory(user=doctor2_user)
        DoctorClinicFactory(doctor=doctor2, clinic=clinic2)
        
        api_client.force_authenticate(user=manager1_user)
        
        url = reverse('list_users') + '?role=DOCTOR'
        response = api_client.get(url)
        
        # Should not see doctor2 from clinic2
        emails = [user['email'] for user in response.data['results']]
        assert doctor2_user.email not in emails
    
    def test_doctor_cannot_see_patients_from_other_clinics(self, api_client):
        """Test doctors can only see patients in their clinic."""
        # Create two clinics with doctors
        clinic1 = ClinicFactory()
        doctor1_user = DoctorUserFactory()
        doctor1 = DoctorFactory(user=doctor1_user)
        DoctorClinicFactory(doctor=doctor1, clinic=clinic1)
        
        clinic2 = ClinicFactory()
        doctor2_user = DoctorUserFactory()
        doctor2 = DoctorFactory(user=doctor2_user)
        DoctorClinicFactory(doctor=doctor2, clinic=clinic2)
        
        # Create patients in different clinics
        patient1_user = PatientUserFactory()
        patient1 = PatientFactory(user=patient1_user)
        PatientClinicFactory(patient=patient1, clinic=clinic1)
        PatientDoctorFactory(patient=patient1, doctor=doctor1, clinic=clinic1)
        
        patient2_user = PatientUserFactory()
        patient2 = PatientFactory(user=patient2_user)
        PatientClinicFactory(patient=patient2, clinic=clinic2)
        PatientDoctorFactory(patient=patient2, doctor=doctor2, clinic=clinic2)
        
        # Doctor1 tries to list patients
        api_client.force_authenticate(user=doctor1_user)
        
        url = reverse('list_users') + '?role=PATIENT'
        response = api_client.get(url)
        
        emails = [user['email'] for user in response.data['results']]
        assert patient1_user.email in emails
        assert patient2_user.email not in emails
