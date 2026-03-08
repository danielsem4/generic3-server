from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import logging
from users.models import Patient
from modules.models import Modules, ClinicModules, PatientModules
from clinics.models import Clinic

logger = logging.getLogger(__name__)

# ============ MODULES CRUD ============
@api_view(['GET', 'POST'])
def module_list_create(request):
    """
    GET: List all modules
    POST: Create a new module
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        modules = Modules.objects.all()
        module_list = [{'id': m.id, 'name': m.module_name, 'description': m.module_description} for m in modules]
        return Response(module_list, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        if not request.user.is_staff:
            return Response({'detail': 'You do not have permission to add modules.'}, status=status.HTTP_403_FORBIDDEN)
        
        module_name = request.data.get('module_name')
        module_description = request.data.get('module_description', '')
        
        if not module_name:
            return Response({'detail': 'Module name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            module, created = Modules.objects.get_or_create(
                module_name=module_name,
                defaults={'module_description': module_description}
            )
            if created:
                return Response({
                    'id': module.id,
                    'name': module.module_name,
                    'description': module.module_description
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({'detail': f'Module "{module_name}" already exists.'}, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            logger.error(f"Error adding module: {e}")
            return Response({'detail': 'An error occurred while adding the module.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def module_detail(request, module_id):
    """
    GET: Retrieve a specific module
    PUT/PATCH: Update a module
    DELETE: Delete a module
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    module = get_object_or_404(Modules, id=module_id)

    if request.method == 'GET':
        return Response({
            'id': module.id,
            'name': module.module_name,
            'description': module.module_description
        }, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        if not request.user.is_staff:
            return Response({'detail': 'You do not have permission to update modules.'}, status=status.HTTP_403_FORBIDDEN)

        module_name = request.data.get('module_name', module.module_name)
        module_description = request.data.get('module_description', module.module_description)

        try:
            module.module_name = module_name
            module.module_description = module_description
            module.save()
            return Response({
                'id': module.id,
                'name': module.module_name,
                'description': module.module_description
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating module: {e}")
            return Response({'detail': 'An error occurred while updating the module.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        if not request.user.is_staff:
            return Response({'detail': 'You do not have permission to delete modules.'}, status=status.HTTP_403_FORBIDDEN)

        if ClinicModules.objects.filter(module=module).exists():
            return Response({'detail': 'Module cannot be deleted as it is associated with clinics.'}, status=status.HTTP_409_CONFLICT)
        
        module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ CLINIC MODULES (Nested Resource) ============
@api_view(['GET', 'POST'])
def clinic_module_list_create(request, clinic_id):
    """
    GET: List all modules for a clinic
    POST: Add a module to a clinic
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    clinic = get_object_or_404(Clinic, id=clinic_id)

    if request.method == 'GET':
        clinic_modules = ClinicModules.objects.filter(clinic=clinic).select_related('module')
        modules_list = [{
            'id': cm.module.id,
            'name': cm.module.module_name,
            'description': cm.module.module_description,
            'is_active': cm.is_active
        } for cm in clinic_modules]
        return Response(modules_list, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        if not (request.user.is_staff or request.user.role == 'CLINIC_MANAGER'):
            return Response({'detail': 'You do not have permission to add clinic modules.'}, status=status.HTTP_403_FORBIDDEN)

        module_id = request.data.get('module_id')
        if not module_id:
            return Response({'detail': 'Module ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        module = get_object_or_404(Modules, id=module_id)
        
        clinic_module, created = ClinicModules.objects.get_or_create(clinic=clinic, module=module)
        
        if created:
            return Response({'detail': 'Clinic module added successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Clinic module already exists.'}, status=status.HTTP_409_CONFLICT)


@api_view(['GET', 'PATCH', 'DELETE'])
def clinic_module_detail(request, clinic_id, module_id):
    """
    GET: Get specific clinic module details
    PATCH: Toggle active status or update clinic module
    DELETE: Remove module from clinic
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    clinic = get_object_or_404(Clinic, id=clinic_id)
    module = get_object_or_404(Modules, id=module_id)
    clinic_module = get_object_or_404(ClinicModules, clinic=clinic, module=module)

    if request.method == 'GET':
        return Response({
            'module_id': module.id,
            'module_name': module.module_name,
            'is_active': clinic_module.is_active
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        if not (request.user.is_staff or request.user.role == 'CLINIC_MANAGER'):
            return Response({'detail': 'You do not have permission to modify clinic modules.'}, status=status.HTTP_403_FORBIDDEN)

        # Toggle or update is_active
        if 'is_active' in request.data:
            clinic_module.is_active = request.data['is_active']
        else:
            clinic_module.is_active = not clinic_module.is_active
        
        clinic_module.save()
        return Response({
            'detail': 'Clinic module updated successfully.',
            'is_active': clinic_module.is_active
        }, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        if not (request.user.is_staff or request.user.role == 'CLINIC_MANAGER'):
            return Response({'detail': 'You do not have permission to delete clinic modules.'}, status=status.HTTP_403_FORBIDDEN)

        clinic_module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ PATIENT MODULES (Nested Resource) ============
@api_view(['GET', 'POST'])
def patient_module_list_create(request, clinic_id, patient_id):
    """
    GET: List all modules for a patient in a clinic
    POST: Add a module to a patient
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    patient = get_object_or_404(Patient, user__id=patient_id)
    clinic = get_object_or_404(Clinic, id=clinic_id)

    if request.method == 'GET':
        patient_modules = PatientModules.objects.filter(
            patient=patient, 
            clinic=clinic
        ).select_related('module')
        
        modules_list = [{
            'id': pm.module.id,
            'name': pm.module.module_name,
            'description': pm.module.module_description,
            'is_active': pm.is_active
        } for pm in patient_modules]
        return Response(modules_list, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        if not (request.user.is_staff or request.user.role == 'DOCTOR'):
            return Response({'detail': 'You do not have permission to add patient modules.'}, status=status.HTTP_403_FORBIDDEN)

        module_id = request.data.get('module_id')
        if not module_id:
            return Response({'detail': 'Module ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        module = get_object_or_404(Modules, id=module_id)

        # Verify clinic has this module
        if not ClinicModules.objects.filter(clinic=clinic, module=module).exists():
            return Response({'detail': 'Clinic does not have this module.'}, status=status.HTTP_400_BAD_REQUEST)

        patient_module, created = PatientModules.objects.get_or_create(
            patient=patient,
            clinic=clinic,
            module=module
        )
        
        if created:
            return Response({'detail': 'Patient module added successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Patient module already exists.'}, status=status.HTTP_409_CONFLICT)


@api_view(['GET', 'PATCH', 'DELETE'])
def patient_module_detail(request, clinic_id, patient_id, module_id):
    """
    GET: Get specific patient module details
    PATCH: Toggle active status or update patient module
    DELETE: Remove module from patient
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)

    patient = get_object_or_404(Patient, user__id=patient_id)
    clinic = get_object_or_404(Clinic, id=clinic_id)
    module = get_object_or_404(Modules, id=module_id)
    patient_module = get_object_or_404(PatientModules, patient=patient, clinic=clinic, module=module)

    if request.method == 'GET':
        return Response({
            'module_id': module.id,
            'module_name': module.module_name,
            'is_active': patient_module.is_active
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        if not (request.user.is_staff or request.user.role == 'DOCTOR'):
            return Response({'detail': 'You do not have permission to modify patient modules.'}, status=status.HTTP_403_FORBIDDEN)

        if 'is_active' in request.data:
            patient_module.is_active = request.data['is_active']
        else:
            patient_module.is_active = not patient_module.is_active
        
        patient_module.save()
        return Response({
            'detail': 'Patient module updated successfully.',
            'is_active': patient_module.is_active
        }, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        if not (request.user.is_staff or request.user.role == 'DOCTOR'):
            return Response({'detail': 'You do not have permission to delete patient modules.'}, status=status.HTTP_403_FORBIDDEN)

        patient_module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)