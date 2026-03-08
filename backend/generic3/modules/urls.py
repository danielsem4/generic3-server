from django.urls import path
from . import views

urlpatterns = [
    # Module CRUD
    path('api/v1/modules/', views.module_list_create, name='module-list-create'),
    path('api/v1/modules/<int:module_id>/', views.module_detail, name='module-detail'),
    
    # Clinic Modules (Nested Resource)
    path('api/v1/clinics/<int:clinic_id>/modules/', views.clinic_module_list_create, name='clinic-module-list'),
    path('api/v1/clinics/<int:clinic_id>/modules/<int:module_id>/', views.clinic_module_detail, name='clinic-module-detail'),

    # Patient Modules (Nested Resource)
    path('api/v1/clinics/<int:clinic_id>/patients/<int:patient_id>/modules/', views.patient_module_list_create, name='patient-module-list'),
    path('api/v1/clinics/<int:clinic_id>/patients/<int:patient_id>/modules/<int:module_id>/', views.patient_module_detail, name='patient-module-detail'),
]