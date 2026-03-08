"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock, Mock

from factories import (
    UserFactory, AdminUserFactory, ClinicManagerUserFactory, 
    DoctorUserFactory, PatientUserFactory, ResearchPatientUserFactory,
    ClinicFactory, ResearchClinicFactory,
    ClinicManagerFactory, DoctorFactory, PatientFactory,
    ManagerClinicFactory, DoctorClinicFactory, PatientClinicFactory,
    PatientDoctorFactory, ModulesFactory, ClinicModulesFactory,
    PatientModulesFactory
)


@pytest.fixture(autouse=True)
def configure_test_settings(settings):
    """Configure Django settings for test environment."""
    settings.DEBUG = True
    settings.SECRET_KEY = 'test-secret-key-for-testing-only'
    
    # Use in-memory database
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    
    # Use local memory cache
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }
    
    # Disable password validators for testing
    settings.AUTH_PASSWORD_VALIDATORS = []
    
    return settings


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """Return a Django REST Framework API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    """Return an API client with authenticated user."""
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return AdminUserFactory()


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def clinic_manager_user():
    """Create a clinic manager user with clinic."""
    user = ClinicManagerUserFactory()
    manager = ClinicManagerFactory(user=user)
    clinic = ClinicFactory()
    ManagerClinicFactory(manager=manager, clinic=clinic)
    return user


@pytest.fixture
def clinic_manager_client(api_client, clinic_manager_user):
    """Return an API client authenticated as clinic manager."""
    api_client.force_authenticate(user=clinic_manager_user)
    return api_client


@pytest.fixture
def doctor_user():
    """Create a doctor user with clinic."""
    user = DoctorUserFactory()
    doctor = DoctorFactory(user=user)
    clinic = ClinicFactory()
    DoctorClinicFactory(doctor=doctor, clinic=clinic)
    return user


@pytest.fixture
def doctor_client(api_client, doctor_user):
    """Return an API client authenticated as doctor."""
    api_client.force_authenticate(user=doctor_user)
    return api_client


@pytest.fixture
def patient_user():
    """Create a patient user with clinic."""
    user = PatientUserFactory()
    patient = PatientFactory(user=user)
    clinic = ClinicFactory()
    PatientClinicFactory(patient=patient, clinic=clinic)
    return user


@pytest.fixture
def patient_client(api_client, patient_user):
    """Return an API client authenticated as patient."""
    api_client.force_authenticate(user=patient_user)
    return api_client


@pytest.fixture
def research_patient_user():
    """Create a research patient user."""
    return ResearchPatientUserFactory()


@pytest.fixture
def clinic():
    """Create a standard clinic."""
    return ClinicFactory()


@pytest.fixture
def research_clinic():
    """Create a research clinic."""
    return ResearchClinicFactory()


@pytest.fixture
def clinic_with_modules(clinic):
    """Create a clinic with modules."""
    modules = [ModulesFactory() for _ in range(3)]
    for module in modules:
        ClinicModulesFactory(clinic=clinic, module=module, active=True)
    return clinic


@pytest.fixture
def mock_boto3_ses():
    """Mock boto3 SES client for email sending."""
    with patch('boto3.client') as mock_client:
        mock_ses = MagicMock()
        mock_client.return_value = mock_ses
        yield mock_ses


@pytest.fixture
def mock_boto3_sns():
    """Mock boto3 SNS client for SMS sending."""
    with patch('boto3.Session') as mock_session:
        mock_sns = MagicMock()
        mock_session.return_value.client.return_value = mock_sns
        yield mock_sns


@pytest.fixture
def mock_send_email():
    """Mock email sending function with proper Response return value."""
    with patch('generic3.messages.sendEmailMessage') as mock:
        # Create a mock response with status_code 200
        mock_response = Mock()
        mock_response.status_code = 200
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_send_sms():
    """Mock SMS sending function."""
    with patch('generic3.messages.sendSMSMessage') as mock:
        yield mock


@pytest.fixture
def mock_static_find():
    """Mock Django static file finder."""
    with patch('django.contrib.staticfiles.finders.find') as mock:
        mock.return_value = '/fake/path/to/static/file.png'
        yield mock
