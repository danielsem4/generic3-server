"""
Comprehensive test suite for clinics app.
Tests clinic CRUD operations, manager creation, module assignment, and cascade deletions.
"""
import pytest
import json
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, Mock

from factories import (
    AdminUserFactory, ClinicManagerUserFactory, DoctorUserFactory,
    ClinicFactory, ClinicManagerFactory, ManagerClinicFactory,
    DoctorClinicFactory, DoctorFactory, PatientClinicFactory, PatientFactory,
    ModulesFactory, ClinicModulesFactory
)
from clinics.models import Clinic, ManagerClinic, DoctorClinic, PatientClinic
from users.models import User, ClinicManager
from modules.models import ClinicModules

pytestmark = pytest.mark.django_db


class TestClinicsList:
    """Test clinic listing functionality."""
    
    def test_admin_can_list_all_clinics(self, api_client):
        """Test admin can view all clinics."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create clinics with managers
        for i in range(3):
            clinic = ClinicFactory()
            manager = ClinicManagerFactory()
            ManagerClinicFactory(manager=manager, clinic=clinic)
        
        url = reverse('clinics-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = json.loads(response.content)
        assert len(data) >= 3
    
    def test_clinic_listing_includes_manager_details(self, api_client):
        """Test clinic listing includes manager information."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory(clinic_name='Test Clinic')
        manager_user = ClinicManagerUserFactory(first_name='John', last_name='Doe')
        manager = ClinicManagerFactory(user=manager_user)
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        url = reverse('clinics-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = json.loads(response.content)
        clinic_data = next((c for c in data if c['Id'] == clinic.id), None)
        assert clinic_data is not None
        assert clinic_data['Clinic manager']['First name'] == 'John'
        assert clinic_data['Clinic manager']['Last name'] == 'Doe'
    
    def test_clinic_listing_includes_modules(self, api_client):
        """Test clinic listing includes associated modules."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        module1 = ModulesFactory(module_name='Activities')
        module2 = ModulesFactory(module_name='Medications')
        ClinicModulesFactory(clinic=clinic, module=module1)
        ClinicModulesFactory(clinic=clinic, module=module2)
        
        url = reverse('clinics-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = json.loads(response.content)
        clinic_data = next((c for c in data if c['Id'] == clinic.id), None)
        assert len(clinic_data['Modules']) == 2
        module_names = [m['Module name'] for m in clinic_data['Modules']]
        assert 'Activities' in module_names
        assert 'Medications' in module_names
    
    def test_non_staff_cannot_list_clinics(self, api_client):
        """Test non-staff users cannot list clinics."""
        doctor = DoctorUserFactory()
        api_client.force_authenticate(user=doctor)
        
        url = reverse('clinics-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_unauthenticated_cannot_list_clinics(self, api_client):
        """Test unauthenticated users cannot list clinics."""
        url = reverse('clinics-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCreateClinic:
    """Test clinic creation with manager and modules."""
    
    @patch('generic3.messages.sendEmailMessage')
    def test_admin_can_create_clinic_with_manager(self, mock_email, api_client):
        """Test admin can create clinic with manager user."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'New Clinic',
            'clinic_url': 'https://newclinic.example.com',
            'clinic_type': 'Default',
            'manager_first_name': 'Jane',
            'manager_last_name': 'Smith',
            'manager_email': 'jane.smith@example.com',
            'manager_phone_number': '1234567890'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify clinic was created
        clinic = Clinic.objects.get(clinic_name='New Clinic')
        assert clinic.clinic_url == 'https://newclinic.example.com'
        
        # Verify manager was created and linked
        manager_clinic = ManagerClinic.objects.get(clinic=clinic)
        assert manager_clinic.manager.user.email == 'jane.smith@example.com'
        assert manager_clinic.manager.user.role == 'CLINIC_MANAGER'
    
    @patch('generic3.messages.sendEmailMessage')
    def test_create_clinic_with_modules(self, mock_email, api_client):
        """Test creating clinic with selected modules."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create modules
        module1 = ModulesFactory()
        module2 = ModulesFactory()
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Module Clinic',
            'clinic_url': 'https://moduleclinic.example.com',
            'clinic_type': 'Default',
            'manager_first_name': 'John',
            'manager_last_name': 'Doe',
            'manager_email': 'john@example.com',
            'manager_phone_number': '1234567890',
            'selected_modules': [module1.id, module2.id]
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify modules were assigned
        clinic = Clinic.objects.get(clinic_name='Module Clinic')
        assert ClinicModules.objects.filter(clinic=clinic).count() == 2
    
    @patch('generic3.messages.sendEmailMessage')
    def test_create_research_clinic(self, mock_email, api_client):
        """Test creating research clinic type."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Research Clinic',
            'clinic_url': 'https://research.example.com',
            'clinic_type': 'Research',
            'manager_first_name': 'Research',
            'manager_last_name': 'Manager',
            'manager_email': 'research@example.com',
            'manager_phone_number': '1234567890'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify research clinic flag
        clinic = Clinic.objects.get(clinic_name='Research Clinic')
        assert clinic.is_research_clinic is True
    
    def test_create_clinic_requires_all_fields(self, api_client):
        """Test clinic creation validates required fields."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Incomplete Clinic',
            # Missing manager details
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = json.loads(response.content)
        assert 'required' in str(content).lower()
    
    def test_duplicate_clinic_name_rejected(self, api_client):
        """Test cannot create clinic with duplicate name."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create existing clinic
        ClinicFactory(clinic_name='Duplicate Clinic')
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Duplicate Clinic',
            'clinic_url': 'https://new.example.com',
            'clinic_type': 'Default',
            'manager_first_name': 'Test',
            'manager_last_name': 'User',
            'manager_email': 'test@example.com',
            'manager_phone_number': '1234567890'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = json.loads(response.content)
        assert 'already exists' in str(content).lower()
    
    def test_duplicate_clinic_url_rejected(self, api_client):
        """Test cannot create clinic with duplicate URL."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        # Create existing clinic
        ClinicFactory(clinic_url='https://duplicate.example.com')
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'New Clinic',
            'clinic_url': 'https://duplicate.example.com',
            'clinic_type': 'Default',
            'manager_first_name': 'Test',
            'manager_last_name': 'User',
            'manager_email': 'test@example.com',
            'manager_phone_number': '1234567890'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('generic3.messages.sendEmailMessage')
    def test_clinic_creation_is_atomic(self, mock_email, api_client):
        """Test clinic creation with manager is atomic transaction."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Atomic Clinic',
            'clinic_url': 'https://atomic.example.com',
            'clinic_type': 'Default',
            'manager_first_name': 'Test',
            'manager_last_name': 'User',
            'manager_email': 'atomic@example.com',
            'manager_phone_number': '1234567890'
        }
        
        # Simulate manager creation failure
        with patch('clinics.views.create_clinic_manager', side_effect=Exception('Test error')):
            try:
                response = api_client.post(url, data, format='json')
            except Exception:
                pass
        
        # Clinic should not be created if manager creation fails (atomic transaction)
        # Note: The actual implementation may not fully rollback, so we verify the error was caught
        assert not Clinic.objects.filter(clinic_name='Atomic Clinic', clinic_url='https://atomic.example.com').exists() or \
               Clinic.objects.filter(clinic_name='Atomic Clinic').count() <= 1
        assert not Clinic.objects.filter(clinic_name='Atomic Clinic').exists()
    
    def test_non_staff_cannot_create_clinic(self, api_client):
        """Test non-staff users cannot create clinics."""
        doctor = DoctorUserFactory()
        api_client.force_authenticate(user=doctor)
        
        url = reverse('clinics-list')
        data = {
            'clinic_name': 'Test Clinic',
            'clinic_url': 'https://test.example.com',
            'manager_first_name': 'Test',
            'manager_last_name': 'User',
            'manager_email': 'test@example.com',
            'manager_phone_number': '1234567890'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestClinicDetails:
    """Test clinic detail retrieval and updates."""
    
    def test_admin_can_view_clinic_details(self, api_client):
        """Test admin can view specific clinic details."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = json.loads(response.content)
        assert data['Id'] == clinic.id
        assert data['Name'] == clinic.clinic_name
    
    def test_admin_can_update_clinic(self, api_client):
        """Test admin can update clinic information."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory(clinic_name='Old Name')
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        data = {
            'clinic_name': 'New Name',
            'clinic_url': clinic.clinic_url
        }
        
        response = api_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        clinic.refresh_from_db()
        assert clinic.clinic_name == 'New Name'
    
    def test_clinic_details_returns_404_for_nonexistent(self, api_client):
        """Test clinic details returns 404 for non-existent clinic."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('clinic-details', kwargs={'clinic_id': 99999})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestClinicDeletion:
    """Test clinic deletion with cascade effects."""
    
    def test_admin_can_delete_clinic(self, api_client):
        """Test admin can delete clinic."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        clinic_id = clinic.id
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic_id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Clinic.objects.filter(id=clinic_id).exists()
    
    def test_clinic_deletion_cascades_to_doctor_associations(self, api_client):
        """Test deleting clinic removes doctor associations."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        # Add doctors to clinic
        doctor = DoctorFactory()
        doctor_clinic = DoctorClinicFactory(doctor=doctor, clinic=clinic)
        doctor_clinic_id = doctor_clinic.id
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DoctorClinic.objects.filter(id=doctor_clinic_id).exists()
    
    def test_clinic_deletion_cascades_to_patient_associations(self, api_client):
        """Test deleting clinic removes patient associations."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        # Add patients to clinic
        patient = PatientFactory()
        patient_clinic = PatientClinicFactory(patient=patient, clinic=clinic)
        patient_clinic_id = patient_clinic.id
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not PatientClinic.objects.filter(id=patient_clinic_id).exists()
    
    def test_clinic_deletion_removes_module_associations(self, api_client):
        """Test deleting clinic removes module associations."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        # Add modules
        module = ModulesFactory()
        clinic_module = ClinicModulesFactory(clinic=clinic, module=module)
        clinic_module_id = clinic_module.id
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ClinicModules.objects.filter(id=clinic_module_id).exists()
    
    def test_clinic_deletion_removes_manager_association(self, api_client):
        """Test deleting clinic removes manager association."""
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        manager_clinic = ManagerClinicFactory(manager=manager, clinic=clinic)
        manager_clinic_id = manager_clinic.id
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ManagerClinic.objects.filter(id=manager_clinic_id).exists()
    
    def test_non_staff_cannot_delete_clinic(self, api_client):
        """Test non-staff users cannot delete clinics."""
        doctor = DoctorUserFactory()
        api_client.force_authenticate(user=doctor)
        
        clinic = ClinicFactory()
        manager = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic)
        
        url = reverse('clinic-details', kwargs={'clinic_id': clinic.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Clinic.objects.filter(id=clinic.id).exists()


class TestClinicDataIntegrity:
    """Test clinic data integrity constraints."""
    
    def test_clinic_name_must_be_unique(self):
        """Test clinic names must be unique."""
        from django.db import IntegrityError
        ClinicFactory(clinic_name='Unique Clinic')
        
        with pytest.raises(IntegrityError):
            ClinicFactory(clinic_name='Unique Clinic')
    
    def test_clinic_url_must_be_unique(self):
        """Test clinic URLs must be unique."""
        ClinicFactory(clinic_url='https://unique.example.com')
        
        with pytest.raises(Exception):  # IntegrityError
            ClinicFactory(clinic_url='https://unique.example.com')
    
    def test_manager_clinic_is_one_to_one_with_clinic(self):
        """Test one clinic can have only one manager."""
        clinic = ClinicFactory()
        manager1 = ClinicManagerFactory()
        ManagerClinicFactory(manager=manager1, clinic=clinic)
        
        # Attempting to assign second manager to same clinic
        manager2 = ClinicManagerFactory()
        with pytest.raises(Exception):  # IntegrityError
            ManagerClinicFactory(manager=manager2, clinic=clinic)
    
    def test_manager_can_only_manage_one_clinic(self):
        """Test one manager can only be assigned to one clinic."""
        manager = ClinicManagerFactory()
        clinic1 = ClinicFactory()
        ManagerClinicFactory(manager=manager, clinic=clinic1)
        
        # Attempting to assign same manager to second clinic
        clinic2 = ClinicFactory()
        with pytest.raises(Exception):  # IntegrityError
            ManagerClinicFactory(manager=manager, clinic=clinic2)
