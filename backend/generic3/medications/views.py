from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework import status
from clinics.models import Clinic
from users.models import Doctor, PatientDoctor, User, Patient
from medications.models import MedicationReport, MedicationsBundle, Medicines, PatientMedicationsBundle, PatientMedicine , ClinicMedicine
from generic3.utils import format_timestamp


############################# MEDICATIONS CRUD #######################################

@api_view(['GET', 'POST'])
def medications_list(request):
    """
    Handle GET and POST requests for medications.
    GET: List all medications base on user role.
    POST: Create a new medication base on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
    
    clinic_id = request.GET.get('clinic_id', None)

    if request.method == 'GET':
        if clinic_id:
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            if user.role == 'DOCTOR':
                doctor = Doctor.objects.filter(user=user).first()
                patient_id = request.GET.get('patient_id', None)                    
                if not doctor:
                    return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
                
                # show patient medications if patient_id is provided
                if patient_id:
                    try:
                        patient_user = User.objects.get(id=patient_id)
                        if patient_user.role != 'PATIENT' and patient_user.role != 'RESEARCH_PATIENT':
                            return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
                    except User.DoesNotExist:
                        return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
                    try:
                        patient = Patient.objects.get(user=patient_user)
                    except Patient.DoesNotExist:
                        return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
                    
                    patient_medications = PatientMedicine.objects.filter(clinic=clinic, patient=patient, doctor=doctor).select_related('medicine')
                    medication_list = [
                        {
                            "id": medication.medicine.id,
                            "name": medication.medicine.medName,
                            "form": medication.medicine.medForm,
                            "unit_of_measurement": medication.medicine.medUnitOfMeasurement
                        } for medication in patient_medications
                    ]
                    return JsonResponse(medication_list, safe=False, status=status.HTTP_200_OK)
                
            # show all clinic medications for the doctor or clinic manager
            clinic_medications = ClinicMedicine.objects.filter(clinic=clinic).select_related('medicine')
            medication_list = [{"id": cm.medicine.id, "name": cm.medicine.medName, "form": cm.medicine.medForm, "unit_of_measurement": cm.medicine.medUnitOfMeasurement} for cm in clinic_medications]
            return JsonResponse(medication_list, safe=False, status=status.HTTP_200_OK)
            
        # admin view all medications across all clinics
        medications = Medicines.objects.all()
        medication_list = [{"id": medication.id, "name": medication.medName, "form": medication.medForm, "unit_of_measurement": medication.medUnitOfMeasurement} for medication in medications]
        return JsonResponse(medication_list, safe=False, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':            
        
        data = request.data
        clinic_id = data.get('clinic_id', None)
        patient_id = data.get('patient_id', None)
        medication_name = data.get('medication_name')
        medication_form = data.get('medication_form')
        medication_unit = data.get('medication_unit')
                
        if not medication_name or not medication_form or not medication_unit:
            return JsonResponse({"detail": "Medication name, form, and unit are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.is_staff:
            if Medicines.objects.filter(medName=medication_name , medForm=medication_form, medUnitOfMeasurement=medication_unit).exists():
                return JsonResponse({"detail": "Medication with this detail already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
            medication = Medicines.objects.create(
                medName=medication_name,
                medForm=medication_form,
                medUnitOfMeasurement=medication_unit
            )
        elif user.role == 'CLINIC_MANAGER':
            clinic = Clinic.objects.filter(id=clinic_id).first()
            if not clinic:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            medication = Medicines.objects.get(
                medName=medication_name,
                medForm=medication_form,
                medUnitOfMeasurement=medication_unit
            )
            ClinicMedicine.objects.create(
                medicine=medication,
                clinic=clinic
            )
        
        elif user.role == 'DOCTOR':
            # assign medication to patient
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            clinic = Clinic.objects.filter(id=clinic_id).first()
            if not clinic:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            medication = Medicines.objects.get(
                medName=medication_name,
                medForm=medication_form,
                medUnitOfMeasurement=medication_unit
            )
            clinic_medications = ClinicMedicine.objects.filter(
                clinic=clinic
            ).select_related('medicine')
            
            if not clinic_medications.filter(medicine=medication).exists():
                return JsonResponse({"detail": "Medication not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            patient_user = User.objects.filter(id=patient_id).first()
            if not patient_user or (patient_user.role != 'PATIENT' and patient_user.role != 'RESEARCH_PATIENT'):
                return JsonResponse({"detail": "Patient user not found"}, status=status.HTTP_404_NOT_FOUND)
            
            patient = Patient.objects.filter(user=patient_user).first()
            if not patient:
                return JsonResponse({"detail": "Patient profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            PatientMedicine.objects.create(
                medicine=medication,
                patient=patient,
                doctor=doctor,
                clinic=clinic
            )
        
        return JsonResponse({"id": medication.id, "name": medication.medName, "form": medication.medForm, "unit": medication.medUnitOfMeasurement}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def medication_detail(request, id):
    """
    Handle GET, PUT, DELETE requests for a specific medication.
    GET: Retrieve medication details base on user role.
    PUT: Update medication details base on user role.
    DELETE: Delete the medication base on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        medication = Medicines.objects.get(id=id)
    except Medicines.DoesNotExist:
        return JsonResponse({"detail": "Medication not found"}, status=status.HTTP_404_NOT_FOUND)

    clinic_id = request.GET.get('clinic_id', None)
    try:
        clinic = Clinic.objects.get(id=clinic_id) if clinic_id else None
    except Clinic.DoesNotExist:
        return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        
    patient_id = request.GET.get('patient_id', None)
    patient = None
    
    # Only retrieve patient if patient_id is provided
    if patient_id:
        try:
            patient_user = User.objects.get(id=patient_id)
            if patient_user.role != 'PATIENT' and patient_user.role != 'RESEARCH_PATIENT':
                return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            patient = Patient.objects.get(user=patient_user)
        except Patient.DoesNotExist:
            return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if user.is_staff:
            # Admin: view base medication (no clinic/patient context needed)
            return JsonResponse({"id": medication.id, "name": medication.medName, "form": medication.medForm, "unit": medication.medUnitOfMeasurement}, status=status.HTTP_200_OK)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: view clinic activity (requires clinic_id)
            if not clinic:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic_medication = ClinicMedicine.objects.get(medicine=medication, clinic=clinic)
                return JsonResponse({"id": clinic_medication.medicine.id, "name": clinic_medication.medicine.medName, "form": clinic_medication.medicine.medForm, "unit": clinic_medication.medicine.medUnitOfMeasurement}, status=status.HTTP_200_OK)
            except ClinicMedicine.DoesNotExist:
                return JsonResponse({"detail": "Medication not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Doctor/Patient: view patient activity (requires clinic_id and patient_id)
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                patient_medication = PatientMedicine.objects.get(medicine=medication, clinic=clinic, patient=patient)
                data = {
                    "id": medication.id,
                    "name": medication.medName,
                    "form": medication.medForm,
                    "unit": medication.medUnitOfMeasurement,
                    "doctor": patient_medication.doctor.user.id,
                    "frequency": patient_medication.frequency,
                    "frequency_data": patient_medication.frequency_data,
                    "start_date": format_timestamp(patient_medication.start_date),
                    "end_date": format_timestamp(patient_medication.end_date),
                    "dosage": patient_medication.dosage
                }
                return JsonResponse(data, status=status.HTTP_200_OK)
            except PatientMedicine.DoesNotExist:
                return JsonResponse({"detail": "Medication not found for this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)      
        
    elif request.method == 'PUT':
        data = request.data
        
        if user.is_staff and not clinic_id and not patient_id:
            # Admin: update base medication (no context params)
            medication.medName = data.get('name', medication.medName)
            medication.medForm = data.get('form', medication.medForm)
            medication.medUnitOfMeasurement = data.get('unit', medication.medUnitOfMeasurement)
            medication.save()
            return JsonResponse({"id": medication.id, "name": medication.medName, "form": medication.medForm, "unit": medication.medUnitOfMeasurement}, status=status.HTTP_200_OK)
        
        elif user.role == 'DOCTOR' and clinic_id and patient_id:
            # Doctor: create or update patient medication assignment
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Verify medication is available in this clinic
            if not ClinicMedicine.objects.filter(clinic=clinic, medicine=medication).exists():
                return JsonResponse({"detail": "Medication not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create patient medication
            patient_medication, created = PatientMedicine.objects.get_or_create(
                medicine=medication,
                patient=patient,
                clinic=clinic,
                defaults={'doctor': doctor}
            )
            
            # Update patient medication details
            patient_medication.frequency = data.get('frequency', patient_medication.frequency)
            patient_medication.frequency_data = data.get('frequency_data', patient_medication.frequency_data)
            patient_medication.start_date = data.get('start_date', patient_medication.start_date)
            patient_medication.end_date = data.get('end_date', patient_medication.end_date)
            patient_medication.save()
            
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            message = "Medication assigned to patient" if created else "Patient medication updated"
            
            return JsonResponse({
                "detail": message,
                "medication_id": medication.id,
                "medication_name": medication.medName,
                "frequency": patient_medication.frequency,
                "frequency_data": patient_medication.frequency_data,
                "start_date": format_timestamp(patient_medication.start_date),
                "end_date": format_timestamp(patient_medication.end_date),
                "dosage": patient_medication.dosage
            }, status=status_code)
        
        else:
            return JsonResponse({"detail": "Invalid request. Admins can update medications, doctors can assign medications to patients."}, status=status.HTTP_403_FORBIDDEN)
    
    elif request.method == 'DELETE':
        if user.is_staff:
            # Admin: delete base medication
            medication.delete()
            return JsonResponse({"detail": "Medication deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: remove medication from clinic (requires clinic_id)
            if not clinic:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic_medication = ClinicMedicine.objects.get(medicine=medication, clinic=clinic)
                clinic_medication.delete()
                return JsonResponse({"detail": "Medication removed from clinic successfully"}, status=status.HTTP_204_NO_CONTENT)
            except ClinicMedicine.DoesNotExist:
                return JsonResponse({"detail": "Medication not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Doctor: remove medication from patient (requires clinic_id and patient_id)
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                patient_medication = PatientMedicine.objects.get(medicine=medication, clinic=clinic, patient=patient)
                patient_medication.delete()
                return JsonResponse({"detail": "Medication removed from patient successfully"}, status=status.HTTP_204_NO_CONTENT)
            except PatientMedicine.DoesNotExist:
                return JsonResponse({"detail": "Medication not found for this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)

################################ MEDICATIONS BUNDLES CRUD #######################################

@api_view(['GET', 'POST'])
def medications_bundles_list(request):
    """
    Handle GET and POST requests for medication bundles.
    GET: List all medication bundles based on user role.
    POST: Create a new medication bundle based on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
    
    clinic_id = request.GET.get('clinic_id', None)

    if request.method == 'GET':
        patient_id = request.GET.get('patient_id', None)
        
        if clinic_id:
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # If patient_id is provided, show patient's assigned bundles
            if patient_id:
                try:
                    patient_user = User.objects.get(id=patient_id)
                    if patient_user.role not in ['PATIENT', 'RESEARCH_PATIENT']:
                        return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
                except User.DoesNotExist:
                    return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
                
                try:
                    patient = Patient.objects.get(user=patient_user)
                except Patient.DoesNotExist:
                    return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
                
                # Doctor viewing patient's bundles
                if user.role == 'DOCTOR':
                    doctor = Doctor.objects.filter(user=user).first()
                    if not doctor:
                        return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
                    
                    # Verify doctor has access to this patient
                    if not PatientDoctor.objects.filter(doctor=doctor, patient=patient, clinic=clinic).exists():
                        return JsonResponse({"detail": "Access denied. Patient not assigned to this doctor."}, status=status.HTTP_403_FORBIDDEN)
                
                # Patient viewing their own bundles
                elif user.role in ['PATIENT', 'RESEARCH_PATIENT']:
                    patient_profile = Patient.objects.filter(user=user).first()
                    if not patient_profile or patient_profile.id != patient.id:
                        return JsonResponse({"detail": "Access denied. You can only view your own bundles."}, status=status.HTTP_403_FORBIDDEN)
                
                # Get patient's assigned bundles
                patient_bundles = PatientMedicationsBundle.objects.filter(
                    patient=patient,
                    bundle__clinic=clinic
                ).select_related('bundle', 'doctor').prefetch_related('bundled_medicines')
                
                bundle_list = [
                    {
                        "id": pb.bundle.id,
                        "bundle_name": pb.bundle.bundle_name,
                        "doctor_id": pb.doctor.user.id,
                        "doctor_name": pb.doctor.user.get_full_name(),
                        "medications": [
                            {
                                "id": medication.id,
                                "name": medication.medName,
                                "form": medication.medForm,
                                "unit_of_measurement": medication.medUnitOfMeasurement
                            } for medication in pb.bundle.medicines.all()
                        ]
                    } for pb in patient_bundles
                ]
                return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
            
            # Get all bundles for specific clinic (no patient_id)
            bundles = MedicationsBundle.objects.filter(clinic=clinic).prefetch_related('medicines')
            bundle_list = [
                {
                    "id": bundle.id,
                    "bundle_name": bundle.bundle_name,
                    "medications": [
                        {
                            "id": medication.id,
                            "name": medication.medName,
                            "form": medication.medForm,
                            "unit_of_measurement": medication.medUnitOfMeasurement
                        } for medication in bundle.medicines.all()
                    ]
                } for bundle in bundles
            ]
            return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
        
        # Admin view all bundles across all clinics
        if user.is_staff:
            bundles = MedicationsBundle.objects.all().prefetch_related('medicines', 'clinic')
            bundle_list = [
                {
                    "id": bundle.id,
                    "bundle_name": bundle.bundle_name,
                    "clinic_id": bundle.clinic.id,
                    "clinic_name": bundle.clinic.clinic_name,
                    "medications": [
                        {
                            "id": medication.id,
                            "name": medication.medName,
                            "form": medication.medForm,
                            "unit_of_measurement": medication.medUnitOfMeasurement
                        } for medication in bundle.medicines.all()
                    ]
                } for bundle in bundles
            ]
            return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
        
        return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'POST':
        data = request.data
        bundle_name = data.get('bundle_name')
        medication_ids = data.get('medication_ids', [])
        
        if not bundle_name:
            return JsonResponse({"detail": "Bundle name is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not medication_ids or not isinstance(medication_ids, list):
            return JsonResponse({"detail": "Medication IDs list is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clinic Manager or Admin can create bundles
        if user.role == 'CLINIC_MANAGER' or user.is_staff:
            if not clinic_id:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if bundle name already exists for this clinic
            if MedicationsBundle.objects.filter(bundle_name=bundle_name, clinic=clinic).exists():
                return JsonResponse({"detail": "Bundle with this name already exists in this clinic"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify all medications exist and belong to the clinic
            medications = Medicines.objects.filter(id__in=medication_ids)
            if medications.count() != len(medication_ids):
                return JsonResponse({"detail": "Some medications not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Verify medications are available in this clinic
            for medication in medications:
                if not ClinicMedicine.objects.filter(clinic=clinic, medicine=medication).exists():
                    return JsonResponse({"detail": f"Medication '{medication.medName}' not available in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            # Create bundle
            bundle = MedicationsBundle.objects.create(
                bundle_name=bundle_name,
                clinic=clinic
            )
            bundle.medicines.set(medications)
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "medications": [{"id": m.id, "name": m.medName} for m in medications]
            }, status=status.HTTP_201_CREATED)
        
        return JsonResponse({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'PUT', 'DELETE'])
def medications_bundle_detail(request, id):
    """
    Handle GET, PUT, DELETE requests for a specific medication bundle.
    GET: Retrieve medication bundle details based on user role.
    PUT: Update medication bundle details based on user role.
    DELETE: Delete the medication bundle based on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        bundle = MedicationsBundle.objects.prefetch_related('medicines').get(id=id)
    except MedicationsBundle.DoesNotExist:
        return JsonResponse({"detail": "Bundle not found"}, status=status.HTTP_404_NOT_FOUND)

    clinic_id = request.GET.get('clinic_id', None)
    patient_id = request.GET.get('patient_id', None)
    
    if request.method == 'GET':
        if user.is_staff:
            # Admin: view any bundle
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "clinic_id": bundle.clinic.id,
                "clinic_name": bundle.clinic.clinic_name,
                "medications": [
                    {
                        "id": medication.id,
                        "name": medication.medName,
                        "form": medication.medForm,
                        "unit_of_measurement": medication.medUnitOfMeasurement
                    } for medication in bundle.medicines.all()
                ]
            }, status=status.HTTP_200_OK)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: view bundle in their clinic
            if not clinic_id:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if bundle.clinic.id != clinic.id:
                return JsonResponse({"detail": "Bundle not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "medications": [
                    {
                        "id": medication.id,
                        "name": medication.medName,
                        "form": medication.medForm,
                        "unit_of_measurement": medication.medUnitOfMeasurement
                    } for medication in bundle.medicines.all()
                ]
            }, status=status.HTTP_200_OK)
        
        elif user.role == 'DOCTOR':
            # Doctor: view bundle details (can view clinic bundles)
            if not clinic_id:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if bundle.clinic.id != clinic.id:
                return JsonResponse({"detail": "Bundle not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "medications": [
                    {
                        "id": medication.id,
                        "name": medication.medName,
                        "form": medication.medForm,
                        "unit_of_measurement": medication.medUnitOfMeasurement
                    } for medication in bundle.medicines.all()
                ]
            }, status=status.HTTP_200_OK)
        
        return JsonResponse({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
    
    elif request.method == 'PUT':
        data = request.data
        
        if user.is_staff or user.role == 'CLINIC_MANAGER':
            # Admin or Clinic Manager: update bundle
            if user.role == 'CLINIC_MANAGER':
                if not clinic_id:
                    return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    clinic = Clinic.objects.get(id=clinic_id)
                except Clinic.DoesNotExist:
                    return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
                
                if bundle.clinic.id != clinic.id:
                    return JsonResponse({"detail": "Bundle not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            bundle.bundle_name = data.get('bundle_name', bundle.bundle_name)
            
            # Update medications if provided
            medication_ids = data.get('medication_ids')
            if medication_ids is not None:
                if not isinstance(medication_ids, list):
                    return JsonResponse({"detail": "Medication IDs must be a list"}, status=status.HTTP_400_BAD_REQUEST)
                
                medications = Medicines.objects.filter(id__in=medication_ids)
                if medications.count() != len(medication_ids):
                    return JsonResponse({"detail": "Some medications not found"}, status=status.HTTP_404_NOT_FOUND)
                
                # Verify medications are available in the clinic
                for medication in medications:
                    if not ClinicMedicine.objects.filter(clinic=bundle.clinic, medication=medication).exists():
                        return JsonResponse({"detail": f"Medication '{medication.medName}' not available in this clinic"}, status=status.HTTP_404_NOT_FOUND)
                
                bundle.medications.set(medications)
            
            bundle.save()
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "medications": [
                    {
                        "id": medication.id,
                        "name": medication.medName,
                        "form": medication.medForm,
                        "unit_of_measurement": medication.medUnitOfMeasurement
                    } for medication in bundle.medications.all()
                ]
            }, status=status.HTTP_200_OK)
        
        elif user.role == 'DOCTOR' and clinic_id and patient_id:
            # Doctor: assign bundle to patient
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if bundle.clinic.id != clinic.id:
                return JsonResponse({"detail": "Bundle not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                patient_user = User.objects.get(id=patient_id)
                if patient_user.role not in ['PATIENT', 'RESEARCH_PATIENT']:
                    return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                patient = Patient.objects.get(user=patient_user)
            except Patient.DoesNotExist:
                return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
            
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Create or get patient bundle assignment
            patient_bundle, created = PatientMedicationsBundle.objects.get_or_create(
                patient=patient,
                bundle=bundle,
                doctor=doctor
            )
            
            message = "Bundle assigned to patient" if created else "Patient already has this bundle"
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            
            return JsonResponse({
                "detail": message,
                "bundle_id": bundle.id,
                "bundle_name": bundle.bundle_name
            }, status=status_code)
        
        return JsonResponse({"detail": "Invalid request. Admins/Clinic Managers can update bundles, doctors can assign bundles to patients."}, status=status.HTTP_403_FORBIDDEN)
    
    elif request.method == 'DELETE':
        if user.is_staff:
            # Admin: delete any bundle
            bundle.delete()
            return JsonResponse({"detail": "Bundle deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: delete bundle from their clinic
            if not clinic_id:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if bundle.clinic.id != clinic.id:
                return JsonResponse({"detail": "Bundle not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            bundle.delete()
            return JsonResponse({"detail": "Bundle deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
        elif user.role == 'DOCTOR' and clinic_id and patient_id:
            # Doctor: remove bundle from patient
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                patient_user = User.objects.get(id=patient_id)
                if patient_user.role not in ['PATIENT', 'RESEARCH_PATIENT']:
                    return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                patient = Patient.objects.get(user=patient_user)
            except Patient.DoesNotExist:
                return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                patient_bundle = PatientMedicationsBundle.objects.get(patient=patient, bundle=bundle)
                patient_bundle.delete()
                return JsonResponse({"detail": "Bundle removed from patient successfully"}, status=status.HTTP_204_NO_CONTENT)
            except PatientMedicationsBundle.DoesNotExist:
                return JsonResponse({"detail": "Bundle not assigned to this patient"}, status=status.HTTP_404_NOT_FOUND)
        
        return JsonResponse({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

################################# PATIENT ACTIVITY LOG #######################################

@api_view(['GET', 'POST'])
def medication_reports(request):
    """
    Handle GET and POST requests for medication reports.
    GET: List all medication reports based on user role.
    POST: Create a new medication report (typically called by patients).
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
    
    clinic_id = request.GET.get('clinic_id', None)
    try:
        clinic = Clinic.objects.get(id=clinic_id) if clinic_id else None
    except Clinic.DoesNotExist:
        return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        
    patient_id = request.GET.get('patient_id', None)
    patient = None
    
    # Only retrieve patient if patient_id is provided
    if patient_id:
        try:
            patient_user = User.objects.get(id=patient_id)
            if patient_user.role != 'PATIENT' and patient_user.role != 'RESEARCH_PATIENT':
                return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            patient = Patient.objects.get(user=patient_user)
        except Patient.DoesNotExist:
            return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        
    if request.method == 'GET':
        if user.is_staff:
            # Admin: view all reports
            reports = MedicationReport.objects.all().select_related('medication', 'patient', 'clinic')
            report_list = [
                {
                    "id": report.id,
                    "medication": {
                        "id": report.medication.id,
                        "name": report.medication.medName,
                        "form": report.medication.medForm,
                        "unit": report.medication.medUnitOfMeasurement
                    },
                    "patient": {
                        "user_id": report.patient.user.id,
                        "name": report.patient.user.get_full_name()
                    },
                    "clinic": {
                        "id": report.clinic.id,
                        "name": report.clinic.clinic_name
                    },
                    "timestamp": format_timestamp(report.timestamp)
                } for report in reports
            ]
            
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: view reports for their clinic
            if not clinic:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            reports = MedicationReport.objects.filter(clinic=clinic).select_related('medication', 'patient', 'clinic')
            report_list = [
                {
                    "id": report.id,
                    "medication": {
                        "id": report.medication.id,
                        "name": report.medication.medName,
                        "form": report.medication.medForm,
                        "unit": report.medication.medUnitOfMeasurement
                    },
                    "patient": {
                        "id": report.patient.id,
                        "user_id": report.patient.user.id,
                        "name": report.patient.user.get_full_name()
                    },
                    "timestamp": format_timestamp(report.timestamp)
                } for report in reports
            ]
            
        elif user.role == 'DOCTOR':
            # Doctor: view reports for their patients
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify doctor has access to this patient
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if not PatientDoctor.objects.filter(doctor=doctor, patient=patient, clinic=clinic).exists():
                return JsonResponse({"detail": "Access denied. Patient not assigned to this doctor."}, status=status.HTTP_403_FORBIDDEN)
            
            reports = MedicationReport.objects.filter(clinic=clinic, patient=patient).select_related('medication')
            report_list = [
                {
                    "id": report.id,
                    "medication": {
                        "id": report.medication.id,
                        "name": report.medication.medName,
                        "form": report.medication.medForm,
                        "unit": report.medication.medUnitOfMeasurement
                    },
                    "timestamp": format_timestamp(report.timestamp)
                } for report in reports
            ]
            
        else:  # PATIENT or RESEARCH_PATIENT
            # Patient: view their own reports
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify patient can only access their own reports
            patient_profile = Patient.objects.filter(user=user).first()
            if not patient_profile or patient_profile.id != patient.id:
                return JsonResponse({"detail": "Access denied. You can only view your own reports."}, status=status.HTTP_403_FORBIDDEN)
            
            reports = MedicationReport.objects.filter(clinic=clinic, patient=patient).select_related('medication')
            report_list = [
                {
                    "id": report.id,
                    "medication": {
                        "id": report.medication.id,
                        "name": report.medication.medName,
                        "form": report.medication.medForm,
                        "unit": report.medication.medUnitOfMeasurement
                    },
                    "timestamp": format_timestamp(report.timestamp)
                } for report in reports
            ]
            
        return JsonResponse(report_list, safe=False, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # POST uses query params for context, request body for actual data
        data = request.data
        medication_id = data.get('medication_id')
        timestamp_str = data.get('timestamp', None)
        
        if not clinic_id or not patient_id:
            return JsonResponse({"detail": "Clinic ID and Patient ID are required in query params"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not medication_id:
            return JsonResponse({"detail": "Medication ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate clinic and patient were already retrieved above
        if not clinic or not patient:
            return JsonResponse({"detail": "Invalid clinic or patient"}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify the patient creating the report is the actual patient
        if user.role in ['PATIENT', 'RESEARCH_PATIENT']:
            patient_profile = Patient.objects.filter(user=user).first()
            if not patient_profile or patient_profile.id != patient.id:
                return JsonResponse({"detail": "You can only create reports for yourself"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            medication = Medicines.objects.get(id=medication_id)
        except Medicines.DoesNotExist:
            return JsonResponse({"detail": "Medication not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify patient has this medication assigned
        if not PatientMedicine.objects.filter(clinic=clinic, patient=patient, medication=medication).exists():
            return JsonResponse({"detail": "Medication not assigned to this patient"}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle timestamp
        if timestamp_str:
            try:
                timestamp = format_timestamp(timestamp_str)
            except (ValueError, TypeError):
                return JsonResponse({"detail": "Invalid timestamp format"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            timestamp = timezone.now()
        
        MedicationReport.objects.create(
            clinic=clinic,
            patient=patient,
            medication=medication,
            timestamp=timestamp
        )
        
        # notification logic will be implemented here in the future
        
        return JsonResponse({"detail": "Medication report created successfully"}, status=status.HTTP_201_CREATED)
