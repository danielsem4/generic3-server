from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from activities.models import Activity, PatientActivity
from clinics.models import Clinic
from users.models import User, Patient
from medications.models import  Medicines, PatientMedicine
from notifications.models import EventNotificationSettings
from generic3.utils import format_timestamp

############ patient side  ###########################################

@api_view(['POST'])
def set_event_notification(request):
    """
    Set event notification for a patient.
    """
    clinic_id = request.data.get('clinic_id')
    patient_id = request.data.get('patient_id')
    event_type = request.data.get('event_type').strip().lower()
    event_id = int(request.data.get('event_id')) # This could be medication ID / activity ID / questionnaire ID

    if not clinic_id or not patient_id or not event_type or not event_id:
        return JsonResponse({"detail": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        clinic = Clinic.objects.get(id=clinic_id)
    except Clinic.DoesNotExist:
        return JsonResponse({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.objects.get(id=patient_id)
        if user.role not in ['PATIENT', 'RESEARCH_PATIENT']:
            return JsonResponse({"detail": "User is not a patient"}, status=status.HTTP_403_FORBIDDEN)
    except User.DoesNotExist:
        return JsonResponse({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        patient = Patient.objects.get(user=user)
    except Patient.DoesNotExist:
        return JsonResponse({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

    if event_type not in ['medication', 'activity', 'questionnaire']:
        return JsonResponse({"detail": "Invalid event type"}, status=status.HTTP_400_BAD_REQUEST)
    
    if event_type == 'medication':
        # Check if the medication exists and is assigned to the patient in the clinic        
        try:
            medication = Medicines.objects.get(id=event_id)
        except Medicines.DoesNotExist:
            return JsonResponse({"detail": "Medication not found"}, status=status.HTTP_404_NOT_FOUND)

        if not PatientMedicine.objects.filter(patient=patient, clinic=clinic, medicine=medication).exists():
            return JsonResponse({"detail": "Medication not assigned to this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
    elif event_type == 'activity':
        try:
            activity = Activity.objects.get(id=event_id)
        except Activity.DoesNotExist:
            return JsonResponse({"detail": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if not PatientActivity.objects.filter(patient=patient, clinic=clinic, activity=activity).exists():
            return JsonResponse({"detail": "Activity not assigned to this patient in this clinic"}, status=status.HTTP_404_NOT_FOUND)
        
    elif event_type == 'questionnaire':
        # Questionnaires logic will be added here
        pass

    frequency = request.data.get('frequency')
    frequency_data = request.data.get('frequency_data')
    start_date_time = request.data.get('start_date_time')
    end_date_time = request.data.get('end_date_time')
    
    if not frequency or not frequency_data:
        frequency = 'once'
        frequency_data = []
    if not start_date_time:
        start_date_time = timezone.now()
    if not end_date_time:
        end_date_time = timezone.now() + timezone.timedelta(days=1)

    if EventNotificationSettings.objects.filter(clinic=clinic, patient=patient, event_type=event_type).exists():
        # update existing notification
        event_notification = EventNotificationSettings.objects.filter(
            clinic=clinic,
            patient=patient,
            event_type=event_type,
            event_id=event_id
        ).update(
            frequency=frequency,
            frequency_data=frequency_data,
            start_date_time=format_timestamp(start_date_time),
            end_date_time=format_timestamp(end_date_time)
        )
    else:
        # create new notification
        event_notification = EventNotificationSettings.objects.create(
            clinic=clinic,
            patient=patient,
            event_type=event_type,
            event_id=event_id,
            frequency=frequency,
            frequency_data=frequency_data,
            start_date_time=format_timestamp(start_date_time),
            end_date_time=format_timestamp(end_date_time)
        )
        if not event_notification:
            return JsonResponse({"detail": f"Failed to set {event_type} notification"}, status=status.HTTP_400_BAD_REQUEST)

    # Notification logic would go here

    return JsonResponse({"detail": f"{event_type} notification set successfully"}, status=status.HTTP_201_CREATED)