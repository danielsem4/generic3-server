from django.core.management.base import BaseCommand
from medications.models import Medicines
import json
import os

class Command(BaseCommand):
    help = 'Load medications from a JSON file into the database'
    
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Loading medications from JSON...'))
        # Load medications from JSON file
        json_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'medications.json')
        with open(json_file_path, 'r', encoding='utf-8') as f:
            medications_json = json.load(f)
        
        for med in medications_json:
            Medicines.objects.create(
                pk=med['pk'],
                medForm=med['fields']['medForm'],
                medName=med['fields']['medName'],
                medUnitOfMeasurement=med['fields']['medUnitOfMeasurement']
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded medications from JSON'))
        self.stdout.write(self.style.SUCCESS('Total medications loaded: {}'.format(Medicines.objects.count())))