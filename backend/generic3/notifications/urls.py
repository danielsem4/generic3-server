from django.urls import path
from . import views

urlpatterns = [
    # patient side 
    path('api/v1/notifications/set/notification/', views.set_event_notification, name='set_event_notification'),

]
