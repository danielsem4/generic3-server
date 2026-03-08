from rest_framework.decorators import api_view
from rest_framework import status
from django.http import JsonResponse
from generic3.utils import format_timestamp
from django.utils import timezone
from users.models import Doctor, PatientDoctor, User, Patient
from .models import Activity, ActivityReport, ClinicActivity, PatientActivity, ActivitiesBundle, PatientActivitiesBundle
from clinics.models import Clinic

############################# ACTIVITIES CRUD #######################################

@api_view(['GET', 'POST'])
def activities_list(request):
    """
    Handle GET and POST requests for activities.
    GET: List all activities base on user role.
    POST: Create a new activity base on user role.
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
                
                # show patient activities if patient_id is provided
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
                    
                    patient_activities = PatientActivity.objects.filter(clinic=clinic, patient=patient, doctor=doctor).select_related('activity')
                    activity_list = [
                        {
                            "id": activity.activity.id,
                            "name": activity.activity.name,
                            "description": activity.activity.description
                        } for activity in patient_activities
                    ]
                    return JsonResponse(activity_list, safe=False, status=status.HTTP_200_OK)
                
            # show all clinic activities for the doctor or clinic manager
            clinic_activities = ClinicActivity.objects.filter(clinic=clinic).select_related('activity')
            activity_list = [{"id": ca.activity.id, "name": ca.activity.name, "description": ca.activity.description} for ca in clinic_activities]
            return JsonResponse(activity_list, safe=False, status=status.HTTP_200_OK)
            
        # admin view all activities
        activities = Activity.objects.all()
        activity_list = [{"id": activity.id, "name": activity.name, "description": activity.description} for activity in activities]
        return JsonResponse(activity_list, safe=False, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':            
        
        data = request.data
        clinic_id = data.get('clinic_id', None)
        patient_id = data.get('patient_id', None)
        name = data.get('name')
        description = data.get('description')
                
        if not name or not description:
            return JsonResponse({"detail": "Name and description are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.is_staff:
            if Activity.objects.filter(name=name).exists():
                return JsonResponse({"detail": "Activity with this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
            activity = Activity.objects.create(
                name=name,
                description=description
            )
        elif user.role == 'CLINIC_MANAGER':
            clinic = Clinic.objects.filter(id=clinic_id).first()
            if not clinic:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            activity = Activity.objects.get(
                name=name,
                description=description
            )
            ClinicActivity.objects.create(
                activity=activity,
                clinic=clinic
            )
        
        elif user.role == 'DOCTOR':
            # assign activity to patient
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            clinic = Clinic.objects.filter(id=clinic_id).first()
            if not clinic:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            activity = Activity.objects.get(
                name=name,
                description=description
            )
            clinic_activities = ClinicActivity.objects.filter(
                clinic=clinic
            ).select_related('activity')
            
            if not clinic_activities.filter(activity=activity).exists():
                return JsonResponse({"detail": "Activity not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            patient_user = User.objects.filter(id=patient_id).first()
            if not patient_user or (patient_user.role != 'PATIENT' and patient_user.role != 'RESEARCH_PATIENT'):
                return JsonResponse({"detail": "Patient user not found"}, status=status.HTTP_404_NOT_FOUND)
            
            patient = Patient.objects.filter(user=patient_user).first()
            if not patient:
                return JsonResponse({"detail": "Patient profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            PatientActivity.objects.create(
                activity=activity,
                patient=patient,
                doctor=doctor,
                clinic=clinic
            )
        
        return JsonResponse({"id": activity.id, "name": activity.name, "description": activity.description}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def activity_detail(request, id):
    """
    Handle GET, PUT, DELETE requests for a specific activity.
    GET: Retrieve activity details base on user role.
    PUT: Update activity details base on user role.
    DELETE: Delete the activity base on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        activity = Activity.objects.get(id=id)
    except Activity.DoesNotExist:
        return JsonResponse({"detail": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)

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
            # Admin: view base activity (no clinic/patient context needed)
            return JsonResponse({"id": activity.id, "name": activity.name, "description": activity.description}, status=status.HTTP_200_OK)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: view clinic activity (requires clinic_id)
            if not clinic:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic_activity = ClinicActivity.objects.get(activity=activity, clinic=clinic)
                return JsonResponse({"id": clinic_activity.activity.id, "name": clinic_activity.activity.name, "description": clinic_activity.activity.description}, status=status.HTTP_200_OK)
            except ClinicActivity.DoesNotExist:
                return JsonResponse({"detail": "Activity not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Doctor/Patient: view patient activity (requires clinic_id and patient_id)
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                patient_activity = PatientActivity.objects.get(activity=activity, clinic=clinic, patient=patient)
                data = {
                    "id": activity.id,
                    "name": activity.name,
                    "description": activity.description,
                    "doctor": patient_activity.doctor.user.id,
                    "frequency": patient_activity.frequency,
                    "frequency_data": patient_activity.frequency_data,
                    "start_date": format_timestamp(patient_activity.start_date),
                    "end_date": format_timestamp(patient_activity.end_date),
                }
                return JsonResponse(data, status=status.HTTP_200_OK)
            except PatientActivity.DoesNotExist:
                return JsonResponse({"detail": "Activity not found for this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)      
        
    elif request.method == 'PUT':
        data = request.data
        
        if user.is_staff and not clinic_id and not patient_id:
            # Admin: update base activity (no context params)
            activity.name = data.get('name', activity.name)
            activity.description = data.get('description', activity.description)
            activity.save()
            return JsonResponse({"id": activity.id, "name": activity.name, "description": activity.description}, status=status.HTTP_200_OK)
        
        elif user.role == 'DOCTOR' and clinic_id and patient_id:
            # Doctor: create or update patient activity assignment
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            doctor = Doctor.objects.filter(user=user).first()
            if not doctor:
                return JsonResponse({"detail": "Doctor profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Verify activity is available in this clinic
            if not ClinicActivity.objects.filter(clinic=clinic, activity=activity).exists():
                return JsonResponse({"detail": "Activity not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create patient activity
            patient_activity, created = PatientActivity.objects.get_or_create(
                activity=activity,
                patient=patient,
                clinic=clinic,
                defaults={'doctor': doctor}
            )
            
            # Update patient activity details
            patient_activity.frequency = data.get('frequency', patient_activity.frequency)
            patient_activity.frequency_data = data.get('frequency_data', patient_activity.frequency_data)
            patient_activity.start_date = data.get('start_date', patient_activity.start_date)
            patient_activity.end_date = data.get('end_date', patient_activity.end_date)
            patient_activity.save()
            
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            message = "Activity assigned to patient" if created else "Patient activity updated"
            
            return JsonResponse({
                "detail": message,
                "activity_id": activity.id,
                "activity_name": activity.name,
                "frequency": patient_activity.frequency,
                "frequency_data": patient_activity.frequency_data,
                "start_date": format_timestamp(patient_activity.start_date),
                "end_date": format_timestamp(patient_activity.end_date)
            }, status=status_code)
        
        else:
            return JsonResponse({"detail": "Invalid request. Admins can update activities, doctors can assign activities to patients."}, status=status.HTTP_403_FORBIDDEN)
    
    elif request.method == 'DELETE':
        if user.is_staff:
            # Admin: delete base activity
            activity.delete()
            return JsonResponse({"detail": "Activity deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        
        elif user.role == 'CLINIC_MANAGER':
            # Clinic Manager: remove activity from clinic (requires clinic_id)
            if not clinic:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic_activity = ClinicActivity.objects.get(activity=activity, clinic=clinic)
                clinic_activity.delete()
                return JsonResponse({"detail": "Activity removed from clinic successfully"}, status=status.HTTP_204_NO_CONTENT)
            except ClinicActivity.DoesNotExist:
                return JsonResponse({"detail": "Activity not found in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Doctor: remove activity from patient (requires clinic_id and patient_id)
            if not clinic or not patient:
                return JsonResponse({"detail": "Clinic ID and Patient ID are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                patient_activity = PatientActivity.objects.get(activity=activity, clinic=clinic, patient=patient)
                patient_activity.delete()
                return JsonResponse({"detail": "Activity removed from patient successfully"}, status=status.HTTP_204_NO_CONTENT)
            except PatientActivity.DoesNotExist:
                return JsonResponse({"detail": "Activity not found for this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)

################################ ACTIVITIES BUNDLES CRUD #######################################

@api_view(['GET', 'POST'])
def activities_bundles_list(request):
    """
    Handle GET and POST requests for activity bundles.
    GET: List all activity bundles based on user role.
    POST: Create a new activity bundle based on user role.
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
                patient_bundles = PatientActivitiesBundle.objects.filter(
                    patient=patient,
                    bundle__clinic=clinic
                ).select_related('bundle', 'doctor').prefetch_related('bundle__activities')
                
                bundle_list = [
                    {
                        "id": pb.bundle.id,
                        "bundle_name": pb.bundle.bundle_name,
                        "doctor_id": pb.doctor.user.id,
                        "doctor_name": pb.doctor.user.get_full_name(),
                        "activities": [
                            {
                                "id": activity.id,
                                "name": activity.name,
                                "description": activity.description
                            } for activity in pb.bundle.activities.all()
                        ]
                    } for pb in patient_bundles
                ]
                return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
            
            # Get all bundles for specific clinic (no patient_id)
            bundles = ActivitiesBundle.objects.filter(clinic=clinic).prefetch_related('activities')
            bundle_list = [
                {
                    "id": bundle.id,
                    "bundle_name": bundle.bundle_name,
                    "activities": [
                        {
                            "id": activity.id,
                            "name": activity.name,
                            "description": activity.description
                        } for activity in bundle.activities.all()
                    ]
                } for bundle in bundles
            ]
            return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
        
        # Admin view all bundles across all clinics
        if user.is_staff:
            bundles = ActivitiesBundle.objects.all().prefetch_related('activities', 'clinic')
            bundle_list = [
                {
                    "id": bundle.id,
                    "bundle_name": bundle.bundle_name,
                    "clinic_id": bundle.clinic.id,
                    "clinic_name": bundle.clinic.clinic_name,
                    "activities": [
                        {
                            "id": activity.id,
                            "name": activity.name,
                            "description": activity.description
                        } for activity in bundle.activities.all()
                    ]
                } for bundle in bundles
            ]
            return JsonResponse(bundle_list, safe=False, status=status.HTTP_200_OK)
        
        return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'POST':
        data = request.data
        bundle_name = data.get('bundle_name')
        activity_ids = data.get('activity_ids', [])
        
        if not bundle_name:
            return JsonResponse({"detail": "Bundle name is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not activity_ids or not isinstance(activity_ids, list):
            return JsonResponse({"detail": "Activity IDs list is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Clinic Manager or Admin can create bundles
        if user.role == 'CLINIC_MANAGER' or user.is_staff:
            if not clinic_id:
                return JsonResponse({"detail": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if bundle name already exists for this clinic
            if ActivitiesBundle.objects.filter(bundle_name=bundle_name, clinic=clinic).exists():
                return JsonResponse({"detail": "Bundle with this name already exists in this clinic"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify all activities exist and belong to the clinic
            activities = Activity.objects.filter(id__in=activity_ids)
            if activities.count() != len(activity_ids):
                return JsonResponse({"detail": "Some activities not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Verify activities are available in this clinic
            for activity in activities:
                if not ClinicActivity.objects.filter(clinic=clinic, activity=activity).exists():
                    return JsonResponse({"detail": f"Activity '{activity.name}' not available in this clinic"}, status=status.HTTP_404_NOT_FOUND)
            
            # Create bundle
            bundle = ActivitiesBundle.objects.create(
                bundle_name=bundle_name,
                clinic=clinic
            )
            bundle.activities.set(activities)
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "activities": [{"id": a.id, "name": a.name} for a in activities]
            }, status=status.HTTP_201_CREATED)
        
        return JsonResponse({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'PUT', 'DELETE'])
def activities_bundle_detail(request, id):
    """
    Handle GET, PUT, DELETE requests for a specific activity bundle.
    GET: Retrieve activity bundle details based on user role.
    PUT: Update activity bundle details based on user role.
    DELETE: Delete the activity bundle based on user role.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        bundle = ActivitiesBundle.objects.prefetch_related('activities').get(id=id)
    except ActivitiesBundle.DoesNotExist:
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
                "activities": [
                    {
                        "id": activity.id,
                        "name": activity.name,
                        "description": activity.description
                    } for activity in bundle.activities.all()
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
                "activities": [
                    {
                        "id": activity.id,
                        "name": activity.name,
                        "description": activity.description
                    } for activity in bundle.activities.all()
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
                "activities": [
                    {
                        "id": activity.id,
                        "name": activity.name,
                        "description": activity.description
                    } for activity in bundle.activities.all()
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
            
            # Update activities if provided
            activity_ids = data.get('activity_ids')
            if activity_ids is not None:
                if not isinstance(activity_ids, list):
                    return JsonResponse({"detail": "Activity IDs must be a list"}, status=status.HTTP_400_BAD_REQUEST)
                
                activities = Activity.objects.filter(id__in=activity_ids)
                if activities.count() != len(activity_ids):
                    return JsonResponse({"detail": "Some activities not found"}, status=status.HTTP_404_NOT_FOUND)
                
                # Verify activities are available in the clinic
                for activity in activities:
                    if not ClinicActivity.objects.filter(clinic=bundle.clinic, activity=activity).exists():
                        return JsonResponse({"detail": f"Activity '{activity.name}' not available in this clinic"}, status=status.HTTP_404_NOT_FOUND)
                
                bundle.activities.set(activities)
            
            bundle.save()
            
            return JsonResponse({
                "id": bundle.id,
                "bundle_name": bundle.bundle_name,
                "activities": [
                    {
                        "id": activity.id,
                        "name": activity.name,
                        "description": activity.description
                    } for activity in bundle.activities.all()
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
            patient_bundle, created = PatientActivitiesBundle.objects.get_or_create(
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
                patient_bundle = PatientActivitiesBundle.objects.get(patient=patient, bundle=bundle)
                patient_bundle.delete()
                return JsonResponse({"detail": "Bundle removed from patient successfully"}, status=status.HTTP_204_NO_CONTENT)
            except PatientActivitiesBundle.DoesNotExist:
                return JsonResponse({"detail": "Bundle not assigned to this patient"}, status=status.HTTP_404_NOT_FOUND)
        
        return JsonResponse({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

################################# PATIENT ACTIVITY LOG #######################################

@api_view(['GET', 'POST'])
def activity_reports(request):
    """
    Handle GET and POST requests for activity reports.
    GET: List all activity reports based on user role.
    POST: Create a new activity report (typically called by patients).
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
            reports = ActivityReport.objects.all().select_related('activity', 'patient', 'clinic')
            report_list = [
                {
                    "id": report.id,
                    "activity": {
                        "id": report.activity.id,
                        "name": report.activity.name,
                        "description": report.activity.description
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
            reports = ActivityReport.objects.filter(clinic=clinic).select_related('activity', 'patient', 'clinic')
            report_list = [
                {
                    "id": report.id,
                    "activity": {
                        "id": report.activity.id,
                        "name": report.activity.name,
                        "description": report.activity.description
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
            
            reports = ActivityReport.objects.filter(clinic=clinic, patient=patient).select_related('activity')
            report_list = [
                {
                    "id": report.id,
                    "activity": {
                        "id": report.activity.id,
                        "name": report.activity.name,
                        "description": report.activity.description
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
            
            reports = ActivityReport.objects.filter(clinic=clinic, patient=patient).select_related('activity')
            report_list = [
                {
                    "id": report.id,
                    "activity": {
                        "id": report.activity.id,
                        "name": report.activity.name,
                        "description": report.activity.description
                    },
                    "timestamp": format_timestamp(report.timestamp)
                } for report in reports
            ]
            
        return JsonResponse(report_list, safe=False, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # POST uses query params for context, request body for actual data
        data = request.data
        activity_id = data.get('activity_id')
        timestamp_str = data.get('timestamp', None)
        
        if not clinic_id or not patient_id:
            return JsonResponse({"detail": "Clinic ID and Patient ID are required in query params"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not activity_id:
            return JsonResponse({"detail": "Activity ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate clinic and patient were already retrieved above
        if not clinic or not patient:
            return JsonResponse({"detail": "Invalid clinic or patient"}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify the patient creating the report is the actual patient
        if user.role in ['PATIENT', 'RESEARCH_PATIENT']:
            patient_profile = Patient.objects.filter(user=user).first()
            if not patient_profile or patient_profile.id != patient.id:
                return JsonResponse({"detail": "You can only create reports for yourself"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return JsonResponse({"detail": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Verify patient has this activity assigned
        if not PatientActivity.objects.filter(clinic=clinic, patient=patient, activity=activity).exists():
            return JsonResponse({"detail": "Activity not assigned to this patient"}, status=status.HTTP_404_NOT_FOUND)
        
        # Handle timestamp
        if timestamp_str:
            try:
                timestamp = format_timestamp(timestamp_str)
            except (ValueError, TypeError):
                return JsonResponse({"detail": "Invalid timestamp format"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            timestamp = timezone.now()
        
        ActivityReport.objects.create(
            clinic=clinic,
            patient=patient,
            activity=activity,
            timestamp=timestamp
        )
        
        # notification logic will be implemented here in the future
        
        return JsonResponse({"detail": "Activity report created successfully"}, status=status.HTTP_201_CREATED)

