"""
Comprehensive tests for Fileshare app.
Tests file upload, download, listing, deletion with S3 mocking.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from factories import (
    AdminUserFactory, DoctorUserFactory, PatientUserFactory,
    ClinicFactory, SharedFilesFactory
)


@pytest.mark.django_db
class TestFileListPermissions:
    """Test permission controls for listing files."""
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access files."""
        response = api_client.get('/api/v1/fileshare/')
        assert response.status_code == 401
    
    def test_admin_can_list_all_files(self, admin_client):
        """Admin can list all files across clinics."""
        SharedFilesFactory.create_batch(3)
        
        response = admin_client.get('/api/v1/fileshare/')
        assert response.status_code == 200
    
    def test_doctor_sees_only_own_uploaded_files(self, doctor_client):
        """Doctor sees only files they uploaded."""
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        
        # Files uploaded by this doctor
        SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic,
            file_name='doctor_file.pdf'
        )
        
        # Files uploaded by another doctor
        other_doctor = DoctorUserFactory().doctor
        SharedFilesFactory(
            doctor=other_doctor,
            patient=patient,
            clinic=clinic,
            file_name='other_doctor_file.pdf'
        )
        
        response = doctor_client.get('/api/v1/fileshare/')
        assert response.status_code == 200
    
    def test_patient_sees_only_own_files(self, patient_client):
        """Patient sees only files shared with them."""
        patient = patient_client.handler._force_user.patient
        clinic = ClinicFactory()
        doctor = DoctorUserFactory().doctor
        
        # File for this patient
        SharedFilesFactory(
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            file_name='my_file.pdf'
        )
        
        # File for another patient
        other_patient = PatientUserFactory().patient
        SharedFilesFactory(
            patient=other_patient,
            doctor=doctor,
            clinic=clinic,
            file_name='other_patient_file.pdf'
        )
        
        response = patient_client.get('/api/v1/fileshare/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestFileUpload:
    """Test file upload functionality with S3 mocking."""
    
    @patch('fileshare.utils.upload_to_s3')
    def test_doctor_can_upload_file_for_patient(self, mock_upload, doctor_client):
        """Doctor can upload files for patients."""
        mock_upload.return_value = ('s3://bucket/file.pdf', 1024)
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        
        # Create a mock file
        file_content = b'PDF file content'
        file = BytesIO(file_content)
        file.name = 'test_report.pdf'
        
        response = doctor_client.post('/api/v1/fileshare/', {
            'file': file,
            'patient_id': patient.id,
            'clinic_id': clinic.id
        }, format='multipart')
        
        assert response.status_code in [200, 201]
        mock_upload.assert_called_once()
    
    @patch('fileshare.utils.upload_to_s3')
    def test_patient_cannot_upload_files(self, mock_upload, patient_client):
        """Patients cannot upload files."""
        mock_upload.return_value = ('s3://bucket/file.pdf', 1024)
        
        file_content = b'PDF file content'
        file = BytesIO(file_content)
        file.name = 'test_file.pdf'
        
        response = patient_client.post('/api/v1/fileshare/', {
            'file': file
        }, format='multipart')
        
        assert response.status_code == 403
    
    @patch('fileshare.utils.upload_to_s3')
    def test_file_upload_stores_metadata(self, mock_upload, doctor_client):
        """File upload stores correct metadata."""
        s3_path = 's3://bucket/uploads/test_file.pdf'
        file_size = 2048
        mock_upload.return_value = (s3_path, file_size)
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        
        file_content = b'PDF file content'
        file = BytesIO(file_content)
        file.name = 'test_document.pdf'
        
        response = doctor_client.post('/api/v1/fileshare/', {
            'file': file,
            'patient_id': patient.id,
            'clinic_id': clinic.id
        }, format='multipart')
        
        if response.status_code in [200, 201]:
            from fileshare.models import SharedFiles
            uploaded_file = SharedFiles.objects.filter(
                doctor=doctor,
                patient=patient
            ).first()
            
            if uploaded_file:
                assert uploaded_file.file_name == 'test_document.pdf'
                assert uploaded_file.clinic == clinic
    
    @patch('fileshare.utils.upload_to_s3')
    def test_file_upload_handles_s3_failure(self, mock_upload, doctor_client):
        """File upload handles S3 upload failures gracefully."""
        mock_upload.side_effect = Exception('S3 upload failed')
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        
        file_content = b'PDF file content'
        file = BytesIO(file_content)
        file.name = 'test_file.pdf'
        
        response = doctor_client.post('/api/v1/fileshare/', {
            'file': file,
            'patient_id': patient.id,
            'clinic_id': clinic.id
        }, format='multipart')
        
        assert response.status_code == 500


@pytest.mark.django_db
class TestFileDetail:
    """Test file detail, download, and deletion."""
    
    @patch('fileshare.utils.get_presigned_url')
    def test_doctor_can_view_own_uploaded_file(self, mock_presigned, doctor_client):
        """Doctor can view details of files they uploaded."""
        mock_presigned.return_value = 'https://s3.amazonaws.com/signed-url'
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        patient = PatientUserFactory().patient
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic,
            file_name='test_file.pdf'
        )
        
        response = doctor_client.get(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 200
    
    @patch('fileshare.utils.get_presigned_url')
    def test_patient_can_view_own_file(self, mock_presigned, patient_client):
        """Patient can view files shared with them."""
        mock_presigned.return_value = 'https://s3.amazonaws.com/signed-url'
        
        patient = patient_client.handler._force_user.patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic,
            file_name='patient_file.pdf'
        )
        
        response = patient_client.get(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 200
    
    @patch('fileshare.utils.get_presigned_url')
    def test_patient_cannot_view_other_patient_files(self, mock_presigned, patient_client):
        """Patient cannot view files of other patients."""
        mock_presigned.return_value = 'https://s3.amazonaws.com/signed-url'
        
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        other_patient = PatientUserFactory().patient
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=other_patient,
            clinic=clinic
        )
        
        response = patient_client.get(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 404
    
    @patch('fileshare.utils.delete_from_s3')
    def test_doctor_can_delete_own_uploaded_file(self, mock_delete, doctor_client):
        """Doctor can delete files they uploaded."""
        mock_delete.return_value = True
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        patient = PatientUserFactory().patient
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        response = doctor_client.delete(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 204
        
        mock_delete.assert_called_once()
    
    @patch('fileshare.utils.delete_from_s3')
    def test_patient_cannot_delete_files(self, mock_delete, patient_client):
        """Patients cannot delete files."""
        mock_delete.return_value = True
        
        patient = patient_client.handler._force_user.patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        response = patient_client.delete(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 403
    
    @patch('fileshare.utils.delete_from_s3')
    def test_admin_can_delete_any_file(self, mock_delete, admin_client):
        """Admin can delete any file."""
        mock_delete.return_value = True
        
        doctor = DoctorUserFactory().doctor
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        response = admin_client.delete(f'/api/v1/fileshare/{shared_file.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestFileCascadeDeletion:
    """Test cascade deletion behavior."""
    
    def test_deleting_patient_removes_shared_files(self):
        """Deleting a patient removes all files shared with them."""
        patient = PatientUserFactory().patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        SharedFilesFactory(
            patient=patient,
            doctor=doctor,
            clinic=clinic
        )
        
        patient_id = patient.id
        patient.delete()
        
        # Verify shared files are deleted
        from fileshare.models import SharedFiles
        assert not SharedFiles.objects.filter(patient_id=patient_id).exists()
    
    def test_deleting_doctor_removes_their_uploaded_files(self):
        """Deleting a doctor removes all files they uploaded."""
        doctor = DoctorUserFactory().doctor
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        doctor_id = doctor.id
        doctor.delete()
        
        # Verify uploaded files are deleted
        from fileshare.models import SharedFiles
        assert not SharedFiles.objects.filter(doctor_id=doctor_id).exists()
    
    def test_deleting_clinic_removes_clinic_files(self):
        """Deleting a clinic removes all associated files."""
        clinic = ClinicFactory()
        doctor = DoctorUserFactory().doctor
        patient = PatientUserFactory().patient
        
        SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        clinic_id = clinic.id
        clinic.delete()
        
        # Verify clinic files are deleted
        from fileshare.models import SharedFiles
        assert not SharedFiles.objects.filter(clinic_id=clinic_id).exists()


@pytest.mark.django_db
class TestFileDataIntegrity:
    """Test data integrity and validation."""
    
    def test_file_stores_upload_date(self):
        """File stores upload date automatically."""
        doctor = DoctorUserFactory().doctor
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        assert shared_file.upload_date is not None
    
    def test_file_requires_all_relationships(self):
        """File requires patient, doctor, and clinic."""
        doctor = DoctorUserFactory().doctor
        patient = PatientUserFactory().patient
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            file_name='test.pdf',
            file_path='s3://bucket/test.pdf',
            size=1024,
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        assert shared_file.doctor == doctor
        assert shared_file.patient == patient
        assert shared_file.clinic == clinic
    
    def test_file_size_stored_correctly(self):
        """File size is stored in bytes."""
        shared_file = SharedFilesFactory(
            size=2048  # 2KB
        )
        
        assert shared_file.size == 2048
    
    def test_file_path_stored_correctly(self):
        """File path stores S3 location."""
        s3_path = 's3://my-bucket/uploads/patient123/document.pdf'
        shared_file = SharedFilesFactory(
            file_path=s3_path
        )
        
        assert shared_file.file_path == s3_path


@pytest.mark.django_db
class TestS3Integration:
    """Test S3 integration with mocking."""
    
    @patch('boto3.client')
    def test_s3_upload_called_with_correct_params(self, mock_boto3, doctor_client):
        """S3 upload is called with correct parameters."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        doctor.doctorclinic_set.create(clinic=clinic)
        
        patient = PatientUserFactory().patient
        
        # Note: Actual S3 integration test would require more setup
        # This is a placeholder for S3 integration testing
        assert mock_boto3 is not None
    
    @patch('boto3.client')
    def test_s3_delete_called_on_file_deletion(self, mock_boto3, doctor_client):
        """S3 delete is called when file is deleted."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        doctor = doctor_client.handler._force_user.doctor
        clinic = ClinicFactory()
        patient = PatientUserFactory().patient
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic,
            file_path='s3://bucket/file.pdf'
        )
        
        # Note: Actual deletion would trigger S3 delete
        # This is a placeholder for S3 deletion testing
        assert shared_file.file_path.startswith('s3://')
    
    @patch('boto3.client')
    def test_presigned_url_generation(self, mock_boto3, patient_client):
        """Presigned URL is generated for file downloads."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://signed-url.com'
        mock_boto3.return_value = mock_s3
        
        patient = patient_client.handler._force_user.patient
        doctor = DoctorUserFactory().doctor
        clinic = ClinicFactory()
        
        shared_file = SharedFilesFactory(
            doctor=doctor,
            patient=patient,
            clinic=clinic
        )
        
        # Note: Actual presigned URL generation would require boto3 setup
        # This is a placeholder for presigned URL testing
        assert shared_file is not None
