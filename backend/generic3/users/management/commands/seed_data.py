import json
import os
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import User, ClinicManager, Doctor, Patient, PatientDoctor
from clinics.models import Clinic, ManagerClinic, DoctorClinic, PatientClinic
from modules.models import Modules, ClinicModules, PatientModules
from activities.models import Activity, ClinicActivity, PatientActivity, ActivityReport
from medications.models import Medicines, ClinicMedicine, PatientMedicine, MedicationReport
from notifications.models import EventNotificationSettings


PASSWORD = 'testpass123'


class Command(BaseCommand):
    help = 'Seed the database with dummy data for development and testing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE(
            'NOTE: Make sure you have run "python manage.py migrate" first.\n'
        ))

        self._load_medications()
        admin, manager_user, doctor1_user, doctor2_user, patient_users = self._create_users()
        clinic = self._create_clinic(manager_user)
        doctor1, doctor2 = self._link_clinic(doctor1_user, doctor2_user, patient_users, clinic)
        self._create_modules(clinic, patient_users)
        activities = self._create_activities(clinic, patient_users, doctor1)
        medicines = self._assign_medications(clinic, patient_users, doctor1)
        self._create_reports(clinic, patient_users, activities, medicines)
        self._create_notifications(clinic, patient_users, medicines, activities)

        self.stdout.write(self.style.SUCCESS('\nSeeding complete!'))
        self.stdout.write('Login credentials for all seeded users: password = testpass123')

    # ------------------------------------------------------------------
    # Step 1 — Load medications JSON
    # ------------------------------------------------------------------

    def _load_medications(self):
        if Medicines.objects.exists():
            self.stdout.write(
                f'[skip] Medicines already loaded ({Medicines.objects.count()} records)'
            )
            return

        self.stdout.write('Step 1: Loading medications from JSON...')
        json_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'medications', 'medications.json'
        )
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data:
            Medicines.objects.create(
                pk=entry['pk'],
                medForm=entry['fields']['medForm'],
                medName=entry['fields']['medName'],
                medUnitOfMeasurement=entry['fields']['medUnitOfMeasurement'],
            )

        self.stdout.write(self.style.SUCCESS(
            f'  Created {Medicines.objects.count()} medicines'
        ))

    # ------------------------------------------------------------------
    # Step 2 — Users
    # ------------------------------------------------------------------

    def _create_users(self):
        self.stdout.write('Step 2: Creating users...')

        admin = self._get_or_create_user(
            email='admin@test.com',
            username='admin',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            extra={'is_staff': True, 'is_superuser': True},
        )

        manager_user = self._get_or_create_user(
            email='manager@test.com',
            username='manager',
            first_name='Clinic',
            last_name='Manager',
            role='CLINIC_MANAGER',
        )
        ClinicManager.objects.get_or_create(user=manager_user)

        doctor1_user = self._get_or_create_user(
            email='doctor1@test.com',
            username='doctor1',
            first_name='Jane',
            last_name='Smith',
            role='DOCTOR',
        )
        Doctor.objects.get_or_create(user=doctor1_user)

        doctor2_user = self._get_or_create_user(
            email='doctor2@test.com',
            username='doctor2',
            first_name='John',
            last_name='Doe',
            role='DOCTOR',
        )
        Doctor.objects.get_or_create(user=doctor2_user)

        patient_specs = [
            ('patient1@test.com', 'patient1', 'Alice', 'Johnson'),
            ('patient2@test.com', 'patient2', 'Bob', 'Williams'),
            ('patient3@test.com', 'patient3', 'Carol', 'Davis'),
        ]
        patient_users = []
        for email, username, first, last in patient_specs:
            user = self._get_or_create_user(
                email=email, username=username,
                first_name=first, last_name=last, role='PATIENT',
            )
            Patient.objects.get_or_create(user=user)
            patient_users.append(user)

        self.stdout.write(self.style.SUCCESS(
            f'  7 users ready (admin, manager, 2 doctors, 3 patients)'
        ))
        return admin, manager_user, doctor1_user, doctor2_user, patient_users

    def _get_or_create_user(self, email, username, first_name, last_name, role, extra=None):
        defaults = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'password': make_password(PASSWORD),
        }
        if extra:
            defaults.update(extra)
        user, created = User.objects.get_or_create(email=email, defaults=defaults)
        status = 'Created' if created else 'Exists '
        self.stdout.write(f'  [{status}] {email}')
        return user

    # ------------------------------------------------------------------
    # Step 3 — Clinic
    # ------------------------------------------------------------------

    def _create_clinic(self, manager_user):
        self.stdout.write('Step 3: Creating clinic...')

        clinic, created = Clinic.objects.get_or_create(
            clinic_name='City Medical Center',
            defaults={
                'clinic_url': 'https://citymedical.test',
                'is_research_clinic': False,
            },
        )
        self.stdout.write(f'  [{"Created" if created else "Exists "}] City Medical Center')

        manager = ClinicManager.objects.get(user=manager_user)
        ManagerClinic.objects.get_or_create(manager=manager, defaults={'clinic': clinic})
        self.stdout.write('  Manager linked to clinic')

        return clinic

    # ------------------------------------------------------------------
    # Step 4 — Doctor/Patient clinic + PatientDoctor links
    # ------------------------------------------------------------------

    def _link_clinic(self, doctor1_user, doctor2_user, patient_users, clinic):
        self.stdout.write('Step 4: Linking doctors and patients to clinic...')

        doctor1 = Doctor.objects.get(user=doctor1_user)
        doctor2 = Doctor.objects.get(user=doctor2_user)

        DoctorClinic.objects.get_or_create(doctor=doctor1, clinic=clinic)
        DoctorClinic.objects.get_or_create(doctor=doctor2, clinic=clinic)
        self.stdout.write('  Both doctors assigned to clinic')

        for user in patient_users:
            patient = Patient.objects.get(user=user)
            PatientClinic.objects.get_or_create(patient=patient, clinic=clinic)
            PatientDoctor.objects.get_or_create(
                patient=patient, doctor=doctor1,
                defaults={'clinic': clinic},
            )
        self.stdout.write(f'  {len(patient_users)} patients linked to clinic and doctor1')

        return doctor1, doctor2

    # ------------------------------------------------------------------
    # Step 5 — Modules
    # ------------------------------------------------------------------

    def _create_modules(self, clinic, patient_users):
        self.stdout.write('Step 5: Creating modules...')

        module_specs = [
            ('Medications', 'Medication management module'),
            ('Activities', 'Activity tracking module'),
            ('Questionnaires', 'Questionnaire module'),
        ]

        modules = []
        for name, desc in module_specs:
            module, created = Modules.objects.get_or_create(
                module_name=name,
                defaults={'module_description': desc},
            )
            modules.append(module)
            ClinicModules.objects.get_or_create(clinic=clinic, module=module)

        for user in patient_users:
            patient = Patient.objects.get(user=user)
            for module in modules:
                PatientModules.objects.get_or_create(
                    patient=patient, clinic=clinic, module=module,
                )

        self.stdout.write(self.style.SUCCESS(
            f'  3 modules assigned to clinic and {len(patient_users)} patients'
        ))

    # ------------------------------------------------------------------
    # Step 6 — Activities
    # ------------------------------------------------------------------

    def _create_activities(self, clinic, patient_users, doctor1):
        self.stdout.write('Step 6: Creating activities...')

        activity_specs = [
            ('Morning Walk', 'A 30-minute walk each morning'),
            ('Blood Pressure Check', 'Measure and record blood pressure'),
            ('Breathing Exercises', 'Deep breathing and relaxation exercises'),
            ('Stretching Routine', 'Full-body stretching for 15 minutes'),
            ('Medication Log Review', 'Review and confirm daily medication intake'),
        ]

        activities = []
        for name, desc in activity_specs:
            activity, _ = Activity.objects.get_or_create(
                name=name, defaults={'description': desc},
            )
            activities.append(activity)
            ClinicActivity.objects.get_or_create(activity=activity, clinic=clinic)

        self.stdout.write(f'  {len(activities)} activities registered for clinic')

        for user in patient_users:
            patient = Patient.objects.get(user=user)
            for activity in activities:
                PatientActivity.objects.get_or_create(
                    activity=activity, patient=patient, clinic=clinic,
                    defaults={
                        'doctor': doctor1,
                        'frequency': 'daily',
                        'frequency_data': [],
                        'start_date': timezone.now(),
                    },
                )

        self.stdout.write(f'  Activities assigned to {len(patient_users)} patients')
        return activities

    # ------------------------------------------------------------------
    # Step 7 — Medications (patient assignments)
    # ------------------------------------------------------------------

    def _assign_medications(self, clinic, patient_users, doctor1):
        self.stdout.write('Step 7: Assigning medications to patients...')

        medicines = list(Medicines.objects.all()[:5])
        if not medicines:
            self.stdout.write(self.style.WARNING('  No medicines found — skipping'))
            return []

        for med in medicines:
            ClinicMedicine.objects.get_or_create(clinic=clinic, medicine=med)

        self.stdout.write(f'  {len(medicines)} medicines registered for clinic')

        for user in patient_users:
            patient = Patient.objects.get(user=user)
            for med in medicines:
                PatientMedicine.objects.get_or_create(
                    patient=patient, medicine=med, clinic=clinic,
                    defaults={
                        'doctor': doctor1,
                        'frequency': 'daily',
                        'frequency_data': [],
                        'dosage': '1 unit',
                        'start_date': timezone.now(),
                    },
                )

        self.stdout.write(f'  Medications assigned to {len(patient_users)} patients')
        return medicines

    # ------------------------------------------------------------------
    # Step 8 — Reports
    # ------------------------------------------------------------------

    def _create_reports(self, clinic, patient_users, activities, medicines):
        self.stdout.write('Step 8: Creating reports...')

        first_patient = Patient.objects.get(user=patient_users[0])
        if ActivityReport.objects.filter(patient=first_patient, clinic=clinic).exists():
            self.stdout.write('  [skip] Reports already exist')
            return

        act_count = 0
        med_count = 0

        for user in patient_users:
            patient = Patient.objects.get(user=user)

            for activity in activities[:3]:
                ActivityReport.objects.create(
                    clinic=clinic,
                    patient=patient,
                    activity=activity,
                )
                act_count += 1

            for i, med in enumerate(medicines[:3]):
                MedicationReport.objects.create(
                    clinic=clinic,
                    patient=patient,
                    medication=med,
                    timestamp=timezone.now() - timedelta(days=i + 1),
                )
                med_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Created {act_count} activity reports, {med_count} medication reports'
        ))

    # ------------------------------------------------------------------
    # Step 9 — Notification settings
    # ------------------------------------------------------------------

    def _create_notifications(self, clinic, patient_users, medicines, activities):
        self.stdout.write('Step 9: Creating notification settings...')

        count = 0
        now = timezone.now()

        for user in patient_users:
            patient = Patient.objects.get(user=user)

            if medicines:
                _, created = EventNotificationSettings.objects.get_or_create(
                    clinic=clinic,
                    patient=patient,
                    event_type='medication',
                    event_id=int(medicines[0].id),
                    defaults={
                        'frequency': 'daily',
                        'frequency_data': [],
                        'start_date_time': now,
                        'end_date_time': now + timedelta(days=30),
                    },
                )
                if created:
                    count += 1

            if activities:
                _, created = EventNotificationSettings.objects.get_or_create(
                    clinic=clinic,
                    patient=patient,
                    event_type='activity',
                    event_id=activities[0].id,
                    defaults={
                        'frequency': 'daily',
                        'frequency_data': [],
                        'start_date_time': now,
                        'end_date_time': now + timedelta(days=30),
                    },
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Created {count} notification settings'
        ))
