import boto3
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.decorators import api_view , permission_classes
from rest_framework.permissions import IsAuthenticated
from notifications.utils import generate_notification_message
from fileshare.utils import upload_file_to_s3_and_DB, view_file_from_s3
from clinics.models import Clinic
from users.models import Doctor, Patient, PatientDoctor, User
from .models import SharedFiles

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def list_files(request):
    """
    List all files or create a new file.
    GET: Retrieve files based on query parameters.
    POST: Upload new file(s).
    """
    user = request.user
    if request.method == 'GET':
        if user.is_staff:
            files = SharedFiles.objects.all().order_by('-upload_date')
        elif user.role == 'CLINIC_MANAGER':
            try:
                clinic_id = request.query_params.get('clinic_id')
                files = SharedFiles.objects.filter(clinic=clinic_id).order_by('-upload_date')
            except Clinic.DoesNotExist:
                return Response({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        elif user.role == 'DOCTOR':
            try:
                clinic_id = request.query_params.get('clinic_id')
                patient_id = request.query_params.get('patient_id')
                files = SharedFiles.objects.filter(clinic=clinic_id, patient=patient_id).order_by('-upload_date')
            except Doctor.DoesNotExist:
                return Response({"detail": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        elif user.role == 'PATIENT' or user.role == 'RESEARCH_PATIENT':
            try:
                patient = Patient.objects.get(user=user)
                files = SharedFiles.objects.filter(patient=patient).order_by('-upload_date')
            except Patient.DoesNotExist:
                return Response({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        data = []
        for file in files:
            data.append({
                "id": file.id,
                "file_name": file.file_name,
                "file_path": file.file_path,
                "size": file.size,
                "upload_date": file.upload_date.isoformat(),
                "clinic_id": file.clinic.clinic_name,
                "patient_id": file.patient.user.first_name + " " + file.patient.user.last_name,
                "doctor_id": file.doctor.user.first_name + " " + file.doctor.user.last_name if file.doctor else None
            })
        return Response(data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        if not (user.role == 'DOCTOR' or user.role == 'PATIENT' or user.role == 'RESEARCH_PATIENT'):
            return Response({"detail": "Only doctors and patients can upload files"}, status=status.HTTP_403_FORBIDDEN)
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({"detail": "patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        clinic_id = request.data.get('clinic_id')
        if not clinic_id:
            return Response({"detail": "clinic_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        files = request.FILES.getlist('files') 
        if not files:
            return Response({"detail": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            return Response({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        patient = Patient.objects.filter(user=patient_id).first() 
        if not patient:
            return Response({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        
        doctor = PatientDoctor.objects.filter(patient=patient , clinic=clinic).first().doctor
        uploaded_files , error = upload_file_to_s3_and_DB(files , clinic , patient , doctor)
        if error:
            return Response({"detail": error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # send notification
        if user.role == 'DOCTOR':
            sender_user = doctor.user
            receiver_user = patient.user
        else:
            sender_user = patient.user
            receiver_user = doctor.user
        title , message = generate_notification_message(sender_user=sender_user, receiver_user=receiver_user, type='file_shared', file_names=[file.file_name for file in uploaded_files])
        # Notification logic to be implemented here
        return Response({"uploaded_files": uploaded_files}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def files_detail(request, id):
    """
    Retrieve or delete a file by its ID.
    GET: Retrieve file details.
    DELETE: Delete the file.
    """
    user = request.user
    try:
        file = SharedFiles.objects.get(id=id)
    except SharedFiles.DoesNotExist:
        return Response({"detail": "File not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        base64_data, content_type = view_file_from_s3(file.file_path , file.file_name)
        if base64_data is None:
            return Response({'detail': 'File not found in S3'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'base64_data': base64_data, 'content_type': content_type})
    elif request.method == 'DELETE':
        if not (user.is_staff or (user.role == 'DOCTOR' and file.doctor and file.doctor.user == user) or (user.role in ['PATIENT', 'RESEARCH_PATIENT'] and file.patient and file.patient.user == user)):
            return Response({"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        s3 = boto3.client('s3',region_name='il-central-1')
        try:
            s3_response = s3.delete_object(Bucket='generic3-bucket', Key=file.file_path)   
            if s3_response['ResponseMetadata']['HTTPStatusCode'] != 204:
                return Response({"error":"Failed to delete file from S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            file.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": f"Error deleting file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
