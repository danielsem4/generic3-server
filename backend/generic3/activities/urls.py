from django.urls import path
from . import views

urlpatterns = [
    
    path('api/v1/activities/', views.activities_list),  # GET list, POST create
    
    path('api/v1/activities/<int:id>/', views.activity_detail), # GET, PUT, DELETE specific

    path('api/v1/activities/bundles/', views.activities_bundles_list), # GET list, POST create

    path('api/v1/activities/bundles/<int:id>/', views.activities_bundle_detail), # GET, PUT, DELETE specific

    path('api/v1/activity-reports/', views.activity_reports),  # GET list, POST create
]