"""
Factory classes for generating test data using factory_boy.
Used across all test files to create consistent, realistic test objects.
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth.hashers import make_password

from users.models import User, ClinicManager, Doctor, Patient, PatientDoctor
from clinics.models import Clinic, ManagerClinic, DoctorClinic, PatientClinic
from modules.models import Modules, ClinicModules, PatientModules
from activities.models import Activity, ClinicActivity, PatientActivity, ActivityReport, ActivitiesBundle
from medications.models import Medicines, ClinicMedicine, PatientMedicine, MedicationReport, MedicationsBundle
from notifications.models import EventNotificationSettings
from fileshare.models import SharedFiles

fake = Faker()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances with different roles."""
    
    class Meta:
        model = User
        django_get_or_create = ('email',)
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone_number = factory.Faker('phone_number')
    password = factory.LazyFunction(lambda: make_password('testpass123'))
    is_active = True
    is_staff = False
    role = 'PATIENT'
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to handle password hashing properly."""
        if 'password' in kwargs and not kwargs['password'].startswith('pbkdf2_'):
            kwargs['password'] = make_password(kwargs['password'])
        return super()._create(model_class, *args, **kwargs)


class AdminUserFactory(UserFactory):
    """Factory for creating Admin users."""
    role = 'ADMIN'
    is_staff = True
    is_superuser = True


class ClinicManagerUserFactory(UserFactory):
    """Factory for creating Clinic Manager users."""
    role = 'CLINIC_MANAGER'


class DoctorUserFactory(UserFactory):
    """Factory for creating Doctor users with profile."""
    role = 'DOCTOR'
    
    @factory.post_generation
    def create_doctor_profile(obj, create, extracted, **kwargs):
        """Create Doctor profile after user creation."""
        if create:
            from users.models import Doctor
            Doctor.objects.get_or_create(user=obj)


class PatientUserFactory(UserFactory):
    """Factory for creating Patient users with profile."""
    role = 'PATIENT'
    
    @factory.post_generation
    def create_patient_profile(obj, create, extracted, **kwargs):
        """Create Patient profile after user creation."""
        if create:
            from users.models import Patient
            Patient.objects.get_or_create(user=obj)


class ResearchPatientUserFactory(UserFactory):
    """Factory for creating Research Patient users."""
    role = 'RESEARCH_PATIENT'


class ClinicFactory(DjangoModelFactory):
    """Factory for creating Clinic instances."""
    
    class Meta:
        model = Clinic
        django_get_or_create = ('clinic_name',)
    
    clinic_name = factory.Sequence(lambda n: f'Clinic {n}')
    clinic_url = factory.LazyAttribute(lambda obj: f'https://{obj.clinic_name.lower().replace(" ", "")}.example.com')
    clinic_image_url = factory.Faker('image_url')
    is_research_clinic = False


class ResearchClinicFactory(ClinicFactory):
    """Factory for creating Research Clinic instances."""
    is_research_clinic = True
    clinic_name = factory.Sequence(lambda n: f'Research Clinic {n}')


class ClinicManagerFactory(DjangoModelFactory):
    """Factory for creating ClinicManager profile instances."""
    
    class Meta:
        model = ClinicManager
    
    user = factory.SubFactory(ClinicManagerUserFactory)


class DoctorFactory(DjangoModelFactory):
    """Factory for creating Doctor profile instances."""
    
    class Meta:
        model = Doctor
        django_get_or_create = ('user',)
    
    user = factory.SubFactory(DoctorUserFactory)


class PatientFactory(DjangoModelFactory):
    """Factory for creating Patient profile instances."""
    
    class Meta:
        model = Patient
        django_get_or_create = ('user',)
    
    user = factory.SubFactory(PatientUserFactory)


class ManagerClinicFactory(DjangoModelFactory):
    """Factory for creating ManagerClinic relationships."""
    
    class Meta:
        model = ManagerClinic
    
    manager = factory.SubFactory(ClinicManagerFactory)
    clinic = factory.SubFactory(ClinicFactory)


class DoctorClinicFactory(DjangoModelFactory):
    """Factory for creating DoctorClinic relationships."""
    
    class Meta:
        model = DoctorClinic
    
    doctor = factory.SubFactory(DoctorFactory)
    clinic = factory.SubFactory(ClinicFactory)


class PatientClinicFactory(DjangoModelFactory):
    """Factory for creating PatientClinic relationships."""
    
    class Meta:
        model = PatientClinic
    
    patient = factory.SubFactory(PatientFactory)
    clinic = factory.SubFactory(ClinicFactory)


class PatientDoctorFactory(DjangoModelFactory):
    """Factory for creating PatientDoctor relationships."""
    
    class Meta:
        model = PatientDoctor
    
    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    clinic = factory.SubFactory(ClinicFactory)


class ModulesFactory(DjangoModelFactory):
    """Factory for creating Module instances."""
    
    class Meta:
        model = Modules
        django_get_or_create = ('module_name',)
    
    module_name = factory.Sequence(lambda n: f'Module {n}')
    module_description = factory.Faker('text', max_nb_chars=200)


class ClinicModulesFactory(DjangoModelFactory):
    """Factory for creating ClinicModules relationships."""
    
    class Meta:
        model = ClinicModules
    
    clinic = factory.SubFactory(ClinicFactory)
    module = factory.SubFactory(ModulesFactory)
    is_active = True


class PatientModulesFactory(DjangoModelFactory):
    """Factory for creating PatientModules relationships."""
    
    class Meta:
        model = PatientModules
    
    patient = factory.SubFactory(PatientFactory)
    clinic = factory.SubFactory(ClinicFactory)
    module = factory.SubFactory(ModulesFactory)
    is_active = True


class ActivityFactory(DjangoModelFactory):
    """Factory for creating Activity instances."""
    
    class Meta:
        model = Activity
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'Activity {n}')
    description = factory.Faker('text', max_nb_chars=200)


class ClinicActivityFactory(DjangoModelFactory):
    """Factory for creating ClinicActivity instances."""
    
    class Meta:
        model = ClinicActivity
    
    activity = factory.SubFactory(ActivityFactory)
    clinic = factory.SubFactory(ClinicFactory)


class PatientActivityFactory(DjangoModelFactory):
    """Factory for creating PatientActivity instances."""
    
    class Meta:
        model = PatientActivity
    
    activity = factory.SubFactory(ActivityFactory)
    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    clinic = factory.SubFactory(ClinicFactory)
    frequency = 'daily'
    frequency_data = factory.LazyFunction(lambda: ['09:00', '14:00'])
    start_date = factory.Faker('date_time_this_year')
    end_date = factory.Faker('future_datetime')


class ActivityReportFactory(DjangoModelFactory):
    """Factory for creating ActivityReport instances."""
    
    class Meta:
        model = ActivityReport
    
    clinic = factory.SubFactory(ClinicFactory)
    patient = factory.SubFactory(PatientFactory)
    activity = factory.SubFactory(ActivityFactory)


class ActivitiesBundleFactory(DjangoModelFactory):
    """Factory for creating ActivitiesBundle instances."""
    
    class Meta:
        model = ActivitiesBundle
    
    bundle_name = factory.Sequence(lambda n: f'Bundle {n}')


class MedicinesFactory(DjangoModelFactory):
    """Factory for creating Medicines instances."""
    
    class Meta:
        model = Medicines
    
    medName = factory.Sequence(lambda n: f'Medication {n}')
    medForm = factory.Faker('random_element', elements=['Tablet', 'Capsule', 'Liquid', 'Injection'])
    medUnitOfMeasurement = factory.Faker('random_element', elements=['mg', 'ml', 'units'])


class ClinicMedicineFactory(DjangoModelFactory):
    """Factory for creating ClinicMedicine instances."""
    
    class Meta:
        model = ClinicMedicine
    
    medicine = factory.SubFactory(MedicinesFactory)
    clinic = factory.SubFactory(ClinicFactory)


class PatientMedicineFactory(DjangoModelFactory):
    """Factory for creating PatientMedicine instances."""
    
    class Meta:
        model = PatientMedicine
    
    medicine = factory.SubFactory(MedicinesFactory)
    patient = factory.SubFactory(PatientFactory)
    clinic = factory.SubFactory(ClinicFactory)
    doctor = factory.SubFactory(DoctorFactory)
    frequency = 'daily'
    dosage = '500mg'


class MedicationReportFactory(DjangoModelFactory):
    """Factory for creating medication report instances."""
    
    class Meta:
        model = MedicationReport
    
    clinic = factory.SubFactory(ClinicFactory)
    patient = factory.SubFactory(PatientFactory)
    medication = factory.SubFactory(MedicinesFactory)


class MedicationsBundleFactory(DjangoModelFactory):
    """Factory for creating MedicationsBundle instances."""
    
    class Meta:
        model = MedicationsBundle
    
    bundle_name = factory.Sequence(lambda n: f'Med Bundle {n}')


class EventNotificationSettingsFactory(DjangoModelFactory):
    """Factory for creating EventNotificationSettings instances."""
    
    class Meta:
        model = EventNotificationSettings
    
    clinic = factory.SubFactory(ClinicFactory)
    patient = factory.SubFactory(PatientFactory)
    event_type = 'medication'
    event_id = 1
    frequency = 'daily'
    frequency_data = factory.LazyFunction(lambda: ['08:00', '20:00'])
    start_date_time = factory.Faker('date_time_this_year')


class SharedFilesFactory(DjangoModelFactory):
    """Factory for creating SharedFiles instances."""
    
    class Meta:
        model = SharedFiles
    
    file_name = factory.Sequence(lambda n: f'file_{n}.pdf')
    file_path = factory.LazyAttribute(lambda obj: f's3://bucket/{obj.file_name}')
    size = factory.Faker('random_int', min=1024, max=10485760)  # 1KB to 10MB
    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    clinic = factory.SubFactory(ClinicFactory)
