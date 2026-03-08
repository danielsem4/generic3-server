from django.urls import path
from . import views

urlpatterns = [
    
    path('api/v1/clinics/', views.clinics_list, name='clinics-list'), # GET - list all clinics, POST - create a new clinic
    path('api/v1/clinics/<int:clinic_id>/', views.clinic_details, name='clinic-details'), # GET - retrieve, PUT - update, DELETE - delete a clinic
]
