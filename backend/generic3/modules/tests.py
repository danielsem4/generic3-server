"""
Comprehensive tests for Modules app.
Tests module CRUD, clinic module assignments, and patient module access.
"""
import pytest
import json
from factories import (
    AdminUserFactory, ClinicManagerUserFactory, DoctorUserFactory, PatientUserFactory,
    ClinicFactory, ModulesFactory, ClinicModulesFactory, PatientModulesFactory
)


@pytest.mark.django_db
class TestModulesListPermissions:
    """Test permission controls for listing modules."""
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access modules."""
        response = api_client.get('/api/v1/modules/')
        assert response.status_code == 401
    
    def test_admin_can_list_all_modules(self, admin_client):
        """Admin can list all modules."""
        ModulesFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/modules/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) >= 3
    
    def test_clinic_manager_can_view_modules(self, api_client):
        """Clinic manager can view modules."""
        manager = ClinicManagerUserFactory()
        clinic = ClinicFactory()
        manager.clinicmanager.managerclinic_set.create(clinic=clinic)
        
        api_client.force_authenticate(user=manager)
        
        response = api_client.get('/api/v1/modules/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestCreateModule:
    """Test module creation with different permissions."""
    
    def test_admin_can_create_module(self, admin_client):
        """Admin can create new modules."""
        response = admin_client.post('/api/v1/modules/', {
            'module_name': 'Activities',
            'module_description': 'Activity tracking module'
        })
        assert response.status_code == 201
    
    def test_module_requires_name(self, admin_client):
        """Module creation requires a name."""
        response = admin_client.post('/api/v1/modules/', {
            'module_description': 'Test Description'
            # Missing module_name
        })
        assert response.status_code == 400
    
    def test_doctor_cannot_create_global_modules(self, doctor_client):
        """Doctors cannot create global modules."""
        response = doctor_client.post('/api/v1/modules/', {
            'module_name': 'Test Module',
            'module_description': 'Test'
        })
        assert response.status_code == 403


@pytest.mark.django_db
class TestModuleDetail:
    """Test retrieving and updating specific modules."""
    
    def test_admin_can_view_module_detail(self, admin_client):
        """Admin can view module details."""
        module = ModulesFactory(module_name='Test Module')
        
        response = admin_client.get(f'/api/v1/modules/{module.id}/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['module_name'] == 'Test Module'
    
    def test_admin_can_update_module(self, admin_client):
        """Admin can update module details."""
        module = ModulesFactory(module_name='Old Name')
        
        response = admin_client.put(f'/api/v1/modules/{module.id}/', {
            'module_name': 'Updated Name',
            'module_description': module.module_description
        }, content_type='application/json')
        assert response.status_code == 200
        
        module.refresh_from_db()
        assert module.module_name == 'Updated Name'
    
    def test_admin_can_delete_module(self, admin_client):
        """Admin can delete modules."""
        module = ModulesFactory()
        
        response = admin_client.delete(f'/api/v1/modules/{module.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestClinicModules:
    """Test clinic-specific module assignments."""
    
    def test_admin_can_assign_module_to_clinic(self, admin_client):
        """Admin can assign modules to clinics."""
        clinic = ClinicFactory()
        module = ModulesFactory()
        
        response = admin_client.post(f'/api/v1/clinics/{clinic.id}/modules/', {
            'module_id': module.id,
            'is_active': True
        })
        assert response.status_code in [200, 201]
    
    def test_clinic_manager_can_view_clinic_modules(self, api_client):
        """Clinic manager can view modules for their clinic."""
        manager = ClinicManagerUserFactory()
        clinic = ClinicFactory()
        manager.clinicmanager.managerclinic_set.create(clinic=clinic)
        
        module = ModulesFactory()
        ClinicModulesFactory(clinic=clinic, module=module, is_active=True)
        
        api_client.force_authenticate(user=manager)
        response = api_client.get(f'/api/v1/clinics/{clinic.id}/modules/')
        assert response.status_code == 200
    
    def test_clinic_manager_can_activate_deactivate_module(self, api_client):
        """Clinic manager can activate/deactivate modules for their clinic."""
        manager = ClinicManagerUserFactory()
        clinic = ClinicFactory()
        manager.clinicmanager.managerclinic_set.create(clinic=clinic)
        
        module = ModulesFactory()
        clinic_module = ClinicModulesFactory(clinic=clinic, module=module, is_active=True)
        
        api_client.force_authenticate(user=manager)
        response = api_client.put(
            f'/api/v1/clinics/{clinic.id}/modules/{module.id}/',
            {'is_active': False},
            format='json'
        )
        assert response.status_code == 200
        
        clinic_module.refresh_from_db()
        assert clinic_module.is_active == False
    
    def test_admin_can_remove_module_from_clinic(self, admin_client):
        """Admin can remove modules from clinics."""
        clinic = ClinicFactory()
        module = ModulesFactory()
        ClinicModulesFactory(clinic=clinic, module=module)
        
        response = admin_client.delete(f'/api/v1/clinics/{clinic.id}/modules/{module.id}/')
        assert response.status_code == 204
    
    def test_doctor_cannot_modify_clinic_modules(self, doctor_client):
        """Doctors cannot modify clinic modules."""
        clinic = ClinicFactory()
        module = ModulesFactory()
        
        response = doctor_client.post(f'/api/v1/clinics/{clinic.id}/modules/', {
            'module_id': module.id
        })
        assert response.status_code == 403


@pytest.mark.django_db
class TestPatientModules:
    """Test patient-specific module assignments."""
    
    def test_doctor_can_assign_module_to_patient(self, doctor_client):
        """Doctor can assign modules to patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        module = ModulesFactory()
        ClinicModulesFactory(clinic=clinic, module=module, is_active=True)
        
        response = doctor_client.post(
            f'/api/v1/clinics/{clinic.id}/patients/{patient.id}/modules/',
            {'module_id': module.id, 'is_active': True}
        )
        assert response.status_code in [200, 201]
    
    def test_patient_can_view_assigned_modules(self, patient_client):
        """Patient can view modules assigned to them."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        module = ModulesFactory(module_name='Activities')
        
        PatientModulesFactory(
            patient=patient,
            clinic=clinic,
            module=module,
            is_active=True
        )
        
        response = patient_client.get(f'/api/v1/clinics/{clinic.id}/patients/{patient.id}/modules/')
        assert response.status_code == 200
    
    def test_doctor_can_deactivate_patient_module(self, doctor_client):
        """Doctor can deactivate modules for patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        module = ModulesFactory()
        patient_module = PatientModulesFactory(
            patient=patient,
            clinic=clinic,
            module=module,
            is_active=True
        )
        
        response = doctor_client.put(
            f'/api/v1/clinics/{clinic.id}/patients/{patient.id}/modules/{module.id}/',
            {'is_active': False},
            format='json'
        )
        assert response.status_code == 200
        
        patient_module.refresh_from_db()
        assert patient_module.is_active == False
    
    def test_patient_cannot_modify_own_modules(self, patient_client):
        """Patients cannot modify their own module assignments."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        module = ModulesFactory()
        
        response = patient_client.post(
            f'/api/v1/clinics/{clinic.id}/patients/{patient.id}/modules/',
            {'module_id': module.id}
        )
        assert response.status_code == 403
    
    def test_doctor_cannot_assign_inactive_clinic_module_to_patient(self, doctor_client):
        """Doctor cannot assign inactive clinic modules to patients."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        module = ModulesFactory()
        ClinicModulesFactory(clinic=clinic, module=module, is_active=False)
        
        response = doctor_client.post(
            f'/api/v1/clinics/{clinic.id}/patients/{patient.id}/modules/',
            {'module_id': module.id}
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestModuleCascadeDeletion:
    """Test cascade deletion behavior."""
    
    def test_deleting_module_removes_clinic_assignments(self):
        """Deleting a module removes all clinic assignments."""
        module = ModulesFactory()
        clinic = ClinicFactory()
        
        ClinicModulesFactory(clinic=clinic, module=module)
        
        module_id = module.id
        module.delete()
        
        # Verify clinic module assignments are deleted
        from modules.models import ClinicModules
        assert not ClinicModules.objects.filter(module_id=module_id).exists()
    
    def test_deleting_module_removes_patient_assignments(self):
        """Deleting a module removes all patient assignments."""
        module = ModulesFactory()
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        PatientModulesFactory(
            patient=patient,
            clinic=clinic,
            module=module
        )
        
        module_id = module.id
        module.delete()
        
        # Verify patient module assignments are deleted
        from modules.models import PatientModules
        assert not PatientModules.objects.filter(module_id=module_id).exists()
    
    def test_deleting_clinic_removes_clinic_modules(self):
        """Deleting a clinic removes its module assignments."""
        clinic = ClinicFactory()
        module = ModulesFactory()
        
        ClinicModulesFactory(clinic=clinic, module=module)
        
        clinic_id = clinic.id
        clinic.delete()
        
        # Verify clinic modules are deleted
        from modules.models import ClinicModules
        assert not ClinicModules.objects.filter(clinic_id=clinic_id).exists()
    
    def test_deleting_patient_removes_patient_modules(self):
        """Deleting a patient removes their module assignments."""
        patient = PatientUserFactory().patient
        module = ModulesFactory()
        clinic = ClinicFactory()
        
        PatientModulesFactory(
            patient=patient,
            clinic=clinic,
            module=module
        )
        
        patient_id = patient.id
        patient.delete()
        
        # Verify patient modules are deleted
        from modules.models import PatientModules
        assert not PatientModules.objects.filter(patient_id=patient_id).exists()


@pytest.mark.django_db
class TestModuleDataIntegrity:
    """Test data integrity and validation."""
    
    def test_module_name_can_be_blank(self):
        """Module name can be blank (model allows it)."""
        module = ModulesFactory(module_name='')
        assert module.module_name == ''
    
    def test_same_module_can_be_assigned_to_multiple_clinics(self):
        """Same module can be assigned to multiple clinics."""
        module = ModulesFactory()
        clinic1 = ClinicFactory()
        clinic2 = ClinicFactory()
        
        ClinicModulesFactory(clinic=clinic1, module=module)
        ClinicModulesFactory(clinic=clinic2, module=module)
        
        assert module.clinicmodules_set.count() == 2
    
    def test_patient_can_have_same_module_across_different_clinics(self):
        """Patient can have same module assigned across different clinics."""
        patient = PatientUserFactory().patient
        module = ModulesFactory()
        clinic1 = ClinicFactory()
        clinic2 = ClinicFactory()
        
        PatientModulesFactory(patient=patient, clinic=clinic1, module=module)
        PatientModulesFactory(patient=patient, clinic=clinic2, module=module)
        
        assert patient.patientmodules_set.count() == 2
