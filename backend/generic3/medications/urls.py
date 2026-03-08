from django.urls import path
from . import views

urlpatterns = [
    
    path('api/v1/medications/', views.medications_list),  # GET list, POST create
    
    path('api/v1/medications/<int:id>/', views.medication_detail), # GET, PUT, DELETE specific

    path('api/v1/medications/bundles/', views.medications_bundles_list), # GET list, POST create

    path('api/v1/medications/bundles/<int:id>/', views.medications_bundle_detail), # GET, PUT, DELETE specific

    path('api/v1/medication-reports/', views.medication_reports),  # GET list, POST create
    
]

