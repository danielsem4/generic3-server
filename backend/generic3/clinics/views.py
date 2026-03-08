from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from activities.models import ActivitiesBundle, ClinicActivity
from medications.models import ClinicMedicine, MedicationsBundle
from generic3.utils import create_clinic_manager
from clinics.models import Clinic, DoctorClinic, ManagerClinic, PatientClinic
from modules.models import Modules, ClinicModules
from django.db import transaction

from users.models import ClinicManager, PatientDoctor, User

@api_view(['GET', 'POST'])
def clinics_list(request):
    """
    List all clinics or create a new clinic.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_staff:
        return JsonResponse({"error": "Permission denied , user is not staff"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'GET':
        clinics = Clinic.objects.all()
    
        clinic_list = []
        
        # Iterate through each clinic to gather details
        for clinic in clinics:
            # Get the clinic manager
            manager_clinic = ManagerClinic.objects.filter(clinic=clinic).select_related('manager').first()
            clinic_manager = {
                    "Id": manager_clinic.manager.user.id,
                    "First name": manager_clinic.manager.user.first_name,
                    "Last name": manager_clinic.manager.user.last_name,
                    "Email": manager_clinic.manager.user.email
                }
            
            # Get the modules associated with the clinic
            clinic_modules = ClinicModules.objects.filter(clinic=clinic).select_related('module')
            clinic_modules_list = [{"Id": module.module.id, "Module name": module.module.module_name} for module in clinic_modules]
        
            # Prepare the response data
            clinic_data = {
                "Id": clinic.id,
                "Name": clinic.clinic_name,
                "Clinic url": clinic.clinic_url,
                "Research clinic": "yes" if clinic.is_research_clinic else "no",
                "Clinic manager": clinic_manager,
                "Modules": clinic_modules_list,
            }
            clinic_list.append(clinic_data)

        return JsonResponse(clinic_list, safe=False, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        data = request.data
        clinic_name = data.get("clinic_name")
        clinic_url = data.get("clinic_url")
        clinic_image_url = data.get("clinic_image_url", "")
        clinic_type = data.get("clinic_type", "Default")
        manager_first_name = data.get("manager_first_name")
        manager_last_name = data.get("manager_last_name")
        manager_email = data.get("manager_email")
        manager_phone_number = data.get("manager_phone_number")
        selected_modules = data.get("selected_modules", [])
        
        # Validate manager details
        if not all([manager_first_name, manager_last_name, manager_email, manager_phone_number]):
            return JsonResponse({"error": "Manager details are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate required fields
        if not all([clinic_name, clinic_url, manager_first_name, manager_last_name, manager_email, manager_phone_number]):
            return JsonResponse({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the clinic already exists
        if Clinic.objects.filter(clinic_name=clinic_name).exists() or Clinic.objects.filter(clinic_url=clinic_url).exists():
            return JsonResponse({"error": "Clinic with this name or URL already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                
                # Create the clinic
                clinic = Clinic.objects.create(
                    clinic_name=clinic_name,
                    clinic_url=clinic_url,
                    clinic_image_url=clinic_image_url,
                    is_research_clinic=clinic_type.lower() == "research"
                )
                
                # Create or update the clinic manager
                response = create_clinic_manager(
                    email=manager_email,
                    first_name=manager_first_name,
                    last_name=manager_last_name,
                    phone_number=manager_phone_number,
                    clinic=clinic
                )
                print(response)
                if response.status_code != status.HTTP_201_CREATED:
                    raise Exception("Failed to create clinic manager")

                # Associate selected modules with the clinic
                for module_id in selected_modules:
                    module = Modules.objects.get(id=module_id)
                    ClinicModules.objects.create(clinic=clinic, module=module)
                    
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        return JsonResponse({"message": "Clinic created successfully"}, status=status.HTTP_201_CREATED)

@api_view(['GET' ,'PUT', 'DELETE'])
def clinic_details(request, clinic_id):
    """
    Retrieve, update, or delete a specific clinic.
    """
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    if request.method == 'GET':
        try:
            clinic = Clinic.objects.get(id=clinic_id)
            
            # Get the clinic manager
            manager_clinic = ManagerClinic.objects.filter(clinic=clinic).select_related('manager').first()
            clinic_manager = None
            if manager_clinic:
                clinic_manager = {
                    "Id": manager_clinic.manager.user.id,
                    "First name": manager_clinic.manager.user.first_name,
                    "Last name": manager_clinic.manager.user.last_name,
                    "Email": manager_clinic.manager.user.email
                }
                
            # Get the modules associated with the clinic
            clinic_modules = ClinicModules.objects.filter(clinic=clinic).select_related('module')
            clinic_modules_list = [{"Id": module.module.id, "Module name": module.module.module_name} for module in clinic_modules]
            
            # Prepare the response data
            clinic_data = {
            "Id": clinic.id,
            "Name": clinic.clinic_name,
            "Clinic url": clinic.clinic_url ,
            "Research clinic": "yes" if clinic.is_research_clinic else "no",
            "Clinic manager": clinic_manager,
            "Modules": clinic_modules_list,
            }
            return JsonResponse(clinic_data, status=status.HTTP_200_OK)
        except Clinic.DoesNotExist:
            return JsonResponse({"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
    
    elif request.method == 'PUT':
        if not user.is_staff and not user.role == 'CLINIC_MANAGER':
            return JsonResponse({"error": "Permission denied , user is not staff or clinic manager"}, status=status.HTTP_403_FORBIDDEN)
    
        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            return JsonResponse({"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        update_fields = {}
        
        # Validate and prepare clinic fields for update
        if "clinic_name" in data:
            new_name = data["clinic_name"]
            if not new_name:
                return JsonResponse({"error": "Clinic name cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
            if new_name != clinic.clinic_name and Clinic.objects.filter(clinic_name=new_name).exists():
                return JsonResponse({"error": "Clinic with this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
            update_fields['clinic_name'] = new_name
        
        if "clinic_url" in data:
            new_url = data["clinic_url"]
            if not new_url:
                return JsonResponse({"error": "Clinic URL cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
            if new_url != clinic.clinic_url and Clinic.objects.filter(clinic_url=new_url).exists():
                return JsonResponse({"error": "Clinic with this URL already exists"}, status=status.HTTP_400_BAD_REQUEST)
            update_fields['clinic_url'] = new_url
        
        if "clinic_image_url" in data:
            update_fields['clinic_image_url'] = data["clinic_image_url"]
        
        if "clinic_type" in data:
            update_fields['is_research_clinic'] = (data["clinic_type"].lower() == "research")

        try:
            with transaction.atomic():
                # Update clinic fields only if there are changes
                if update_fields:
                    Clinic.objects.filter(id=clinic_id).update(**update_fields)


                # Update the modules associated with the clinic
                ClinicModules.objects.filter(clinic=clinic).delete()
                
                if "selected_modules" in data:
                    selected_modules = data["selected_modules"]
                    
                for module_id in selected_modules:
                    try:
                        module = Modules.objects.get(id=module_id)
                        ClinicModules.objects.create(clinic=clinic, module=module)
                    except Modules.DoesNotExist:
                        return JsonResponse({"error": f"Module with id {module_id} not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return JsonResponse({"message": "Clinic updated successfully"}, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        if not user.is_staff:
            return JsonResponse({"error": "Permission denied , user is not staff"}, status=status.HTTP_403_FORBIDDEN)
        if not Clinic.objects.filter(id=clinic_id).exists():
            return JsonResponse({"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            # Delete the clinic and its related modules
            with transaction.atomic():
                clinic = Clinic.objects.get(id=clinic_id)
                # delete clinic medications and bundles
                ClinicMedicine.objects.filter(clinic=clinic).delete()
                MedicationsBundle.objects.filter(clinic=clinic).delete()
                # delete the clinic activities and bundles
                ClinicActivity.objects.filter(clinic=clinic).delete()
                ActivitiesBundle.objects.filter(clinic=clinic).delete()
                # delete the clinic modules
                ClinicModules.objects.filter(clinic=clinic).delete()
                # delete associations with doctors and patients
                DoctorClinic.objects.filter(clinic=clinic).delete()
                PatientClinic.objects.filter(clinic=clinic).delete()
                PatientDoctor.objects.filter(clinic=clinic).delete()
                # delete the clinic manager
                if ManagerClinic.objects.filter(clinic=clinic).exists():
                    manager_clinic = ManagerClinic.objects.get(clinic=clinic)
                    clinic_manager = manager_clinic.manager
                    ClinicManager.objects.filter(user=clinic_manager.user).delete()
                    # also delete the user
                    User.objects.filter(id=clinic_manager.user.id).delete()
                    manager_clinic.delete()
                # finally delete the clinic itself
                clinic.delete()
            return JsonResponse({"message": "Clinic deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        