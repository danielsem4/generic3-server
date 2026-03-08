from django.http import JsonResponse
from django.shortcuts import render

# from questionnaires.models import Measurements

def get_all_questionnaires(request):
    # questionnaires = Measurements.objects.all()
    return JsonResponse({'questionnaires': []})