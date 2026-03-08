from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.hashers import make_password
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from modules.models import ClinicModules, PatientModules
from generic3.utils import generate_temporary_password, get_clinic_id_for_user, send_temporary_password_email
from users.models import Doctor, Patient, PatientDoctor, User, ClinicManager
from users.serializers import UserSerializer, UserDetailSerializer, UserCreateSerializer
from clinics.models import Clinic , DoctorClinic, ManagerClinic, PatientClinic


class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    List all users or create a new user.
    GET: Returns paginated list of users filtered by role
    POST: Creates a new user and assigns to clinic
    """
    user = request.user
    site = f"http://{request.get_host()}"
    print("user:" , user)
    if user.role in ['PATIENT', 'RESEARCH_PATIENT']:
        return Response(
            {"error": "Permission denied, user is not staff"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    clinic_id = get_clinic_id_for_user(user , site=site)
    print("clinic_id:", clinic_id)
    clinic = Clinic.objects.get(id=clinic_id) if clinic_id else None
    if request.method == 'GET':
        role_param = request.GET.get('role', None)
        requested_role = role_param.upper() if role_param else None
        if not user.is_staff and not requested_role:
            return Response(
                {"error": "Permission denied, role parameter is required for non-staff users"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        users = User.objects.filter(role=requested_role) if requested_role else User.objects.all()

        if user.role == 'CLINIC_MANAGER' and requested_role in ['DOCTOR', 'PATIENT', 'RESEARCH_PATIENT']:
            users = users.filter(
                id__in=DoctorClinic.objects.filter(clinic=clinic_id).values_list('doctor__user__id', flat=True)
            ) if requested_role == 'DOCTOR' else users.filter(
                id__in=PatientClinic.objects.filter(clinic=clinic_id).values_list('patient__user__id', flat=True)
            )
            
        elif user.role == 'DOCTOR' and requested_role in ['PATIENT', 'RESEARCH_PATIENT']:
            doctor = Doctor.objects.get(user=user)
            patients = PatientClinic.objects.filter(clinic=clinic_id).values_list('patient__user__id', flat=True)
            doctor_patients = PatientDoctor.objects.filter(doctor=doctor).values_list('patient__user__id', flat=True)
            patients = set(patients).intersection(set(doctor_patients)) # only patients of this doctor in this clinic
            users = users.filter(id__in=patients)

        # Apply pagination
        paginator = UserPagination()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(paginated_users, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    elif request.method == 'POST':
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        email = data.get('email')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone_number = data.get('phone_number', '')
        password = data.get('password', None)

        # Use atomic transaction to ensure rollback if clinic assignment fails
        try:
            with transaction.atomic():
                # Check if user already exists
                existing_user = None
                try:
                    existing_user = User.objects.get(email=email)
                except User.DoesNotExist:
                    # Check by phone number if email doesn't exist
                    if phone_number:
                        try:
                            existing_user = User.objects.get(phone_number=phone_number)
                        except User.DoesNotExist:
                            pass
                
                if existing_user:
                    # User exists, validate the data matches
                    if (existing_user.first_name != first_name or 
                        existing_user.last_name != last_name or 
                        existing_user.phone_number != phone_number or
                        existing_user.email != email):
                        return Response(
                            {"detail": "User exists but provided data doesn't match existing user"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Data matches, use existing user and skip to clinic assignment
                    new_user = existing_user 
                    
                else:
                    # User doesn't exist, create new user
                    if clinic and clinic.is_research_clinic and user.role == 'DOCTOR':
                        role = 'RESEARCH_PATIENT'
                        if not password:
                            return Response(
                                {"detail": "Password is required for research patients"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        passw = make_password(password)
                    else: # Generate temporary password and send email
                        passw = generate_temporary_password()
                        response = send_temporary_password_email(email, passw, clinic.clinic_url if clinic else '')
                        if response.status_code != 200:
                            return response
                        
                    if user.role == 'CLINIC_MANAGER':
                        role = 'DOCTOR'
                    elif user.role == 'DOCTOR' and not clinic.is_research_clinic:
                        role = 'PATIENT'
                        
                    # Create the user
                    new_user = User.objects.create(
                        email=email,
                        username=email,  # Use email as username
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        password=passw,
                        role=role,
                    )

                # Add the user to the clinic 
                if new_user.role == 'DOCTOR':
                    doctor, created = Doctor.objects.get_or_create(user=new_user)
                    DoctorClinic.objects.get_or_create(doctor=doctor, clinic=clinic)
                elif new_user.role == 'PATIENT' or new_user.role == 'RESEARCH_PATIENT':
                    patient, created = Patient.objects.get_or_create(user=new_user)
                    doctor = Doctor.objects.get(user=user)
                    if doctor:
                        PatientDoctor.objects.get_or_create(patient=patient, doctor=doctor, clinic=clinic)        
                    PatientClinic.objects.get_or_create(patient=patient, clinic=clinic)
                    clinic_modules = ClinicModules.objects.filter(clinic=clinic)
                    for module in clinic_modules:
                        PatientModules.objects.get_or_create(patient=patient, clinic=clinic, module=module.module)
                else:
                    return Response(
                        {"detail": "User role is not supported"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                return Response(
                    {"detail": "User added to clinic successfully", "user_id": new_user.id}, 
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            return Response(
                {"detail": f"Failed to create user and assign to clinic: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """
    Retrieve, update or delete a user by id.
    GET: Get user details with patient modules if applicable
    PUT: Full update of user details
    PATCH: Partial update of user details
    DELETE: Admin - delete user or remove user from clinic , non-admin staff - remove user from clinic
    """
    current_user = request.user
    site = f"http://{request.get_host()}"
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    clinic_id = get_clinic_id_for_user(current_user , site=site)
    print("clinic_id:", clinic_id)
    
    if request.method == 'GET':
        serializer = UserDetailSerializer(user, context={'clinic_id': clinic_id})
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = UserSerializer(user, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "User updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if current_user.role in ['PATIENT', 'RESEARCH_PATIENT']:
            return Response(
                {"detail": "Permission denied, user is not staff"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user == current_user:
            return Response({"detail": "Cannot delete yourself"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Admin can permanently delete users
        if current_user.role == 'ADMIN':
            # Prevent deletion if user has critical relationships
            if user.role == 'DOCTOR':
                doctor = Doctor.objects.filter(user=user).first()
                if doctor and PatientDoctor.objects.filter(doctor=doctor).exists():
                    return Response(
                        {"detail": "Cannot delete doctor with assigned patients. Remove patients first."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif user.role == 'CLINIC_MANAGER':
                return Response(
                    {"detail": "Cannot delete clinic manager - Only via clinic management"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif user.role in ['PATIENT', 'RESEARCH_PATIENT']:
                patient = Patient.objects.filter(user=user).first()
                if patient and PatientDoctor.objects.filter(patient=patient).exists():
                    return Response(
                        {"detail": "Cannot delete patient with assigned doctors. Remove doctor assignments first."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Permanently delete the user
            user.delete()
            return Response({"detail": "User permanently deleted"}, status=status.HTTP_200_OK)
        
        # Non-admin staff can only remove users from clinic
        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            return Response({"detail": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Permission checks for clinic removal
        if current_user.role == 'CLINIC_MANAGER':
            clinic_manager = ClinicManager.objects.get(user=current_user)
            manager_clinic = ManagerClinic.objects.get(manager=clinic_manager).clinic
            if clinic != manager_clinic:
                return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'DOCTOR' and current_user.role == 'DOCTOR':
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'DOCTOR' and current_user.role == 'CLINIC_MANAGER':
            doctor = Doctor.objects.get(user=user)
            if PatientDoctor.objects.filter(doctor=doctor, clinic=clinic).exists():
                return Response(
                    {"detail": "Cannot remove doctor with assigned patients"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            DoctorClinic.objects.filter(doctor=doctor, clinic=clinic).delete()
        elif current_user.role in ['DOCTOR', 'CLINIC_MANAGER'] and user.role in ['PATIENT', 'RESEARCH_PATIENT']:
            patient = Patient.objects.get(user=user)
            PatientClinic.objects.filter(patient=patient, clinic=clinic).delete()
            PatientDoctor.objects.filter(patient=patient, clinic=clinic).delete()
        else:
            return Response(
                {"detail": "User role cannot be removed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({"detail": "User removed from clinic successfully"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get the current authenticated user's profile.
    GET: Returns current user details with patient modules if applicable
    """
    user = request.user
    site = f"http://{request.get_host()}"
    clinic_id = get_clinic_id_for_user(user, site=site)
    
    serializer = UserDetailSerializer(user, context={'clinic_id': clinic_id})
    return Response(serializer.data, status=status.HTTP_200_OK)
