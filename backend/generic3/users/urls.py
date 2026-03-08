from django.urls import path
from . import views

urlpatterns = [
    path('api/v1/users/', views.list_users, name='list_users'), # POST create user, GET list users
    path('api/v1/users/me/', views.current_user, name='current_user'), # GET current user profile
    path('api/v1/users/<int:user_id>/', views.user_detail, name='user_detail'), # GET, PUT, PATCH, DELETE user by id
]
