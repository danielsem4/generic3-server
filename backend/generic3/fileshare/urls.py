from django.urls import path
from . import views

urlpatterns = [
    path('api/v1/fileshare/', views.list_files, name='list_files'), # GET: list files, POST: upload files
    path('api/v1/fileshare/<int:id>/', views.files_detail, name='files_detail'), # GET: view file, DELETE: delete file
]
