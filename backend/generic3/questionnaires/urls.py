from django.urls import path
from . import views

urlpatterns = [
    # admin questionnaire management
    path('api/v1/questionnaires/', views.get_all_questionnaires, name='get_all_questionnaires'),
]