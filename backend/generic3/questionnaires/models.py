from django.db import models
from clinics.models import Clinic

MeasurementTypes = (
    ('measurement','measurement'),
    ('questionnaire','questionnaire'),
)

object_types = (
    ('short text','text'),
    ('image','image'),
    ('button','button'),
    ('file','file'),
    ('toggle','toggle'),
    ('slider','slider'),
    ('scale','scale'),
    ('paragraph','paragraph'),
    ('checkbox','checkbox'),
    ('radio','radio'),
    ('dropdown','dropdown'),
    ('audio','audio'),
    ('calendar','calendar'),
)

languages = (
    ('he','Hebrew'),
    ('en','English'),
)

class Questionnaire(models.Model):
    name = models.CharField(("questionnaire name"),max_length=1000)
    type = models.CharField(("questionnaire type"), choices=MeasurementTypes, max_length=20, default='measurement')
    is_module = models.BooleanField(('is module?'),default=False)
    language = models.CharField(("language"), choices=languages, max_length=5, default='en')
    is_public = models.BooleanField(('is public?'),default=False)
    is_active = models.BooleanField(('is active?'),default=True)
    is_visible = models.BooleanField(('is visible?'),default=True)
    order_important = models.BooleanField(('order important'),default=False)
    def __str__(self):
        return self.name


class QuestionnaireObjects(models.Model):
    questionnaire = models.ForeignKey(Questionnaire, related_name='measurement_objects', on_delete=models.CASCADE)
    object_type = models.CharField(("object type"), choices=object_types, max_length=20, default='text')
    object_name = models.CharField(("object name"), max_length=1000)
    object_description = models.CharField(("object description"), max_length=1000, blank=True)
    has_options = models.BooleanField(('has options'),default=False)
    options = models.CharField(("options"), max_length=1000, blank=True) # Comma-separated values
    random_selection_of_options = models.BooleanField(('random selection of options'),default=False)
    object_screen = models.IntegerField(("object screen")) # will be set automatically
    object_order = models.IntegerField(("object order")) # will be set automatically
    expected_answer = models.CharField(("expected answer"), max_length=1000, blank=True)
    required = models.BooleanField(('required'), default=False)
    
    def __str__(self):
        return (f"Object Name: {self.object_name}, "
                f"Object Description: {self.object_description}, "
                f"Has Options: {self.has_options}, "
                f"Options: {self.options}, "
                f"Random Selection of Options: {self.random_selection_of_options}, "
                f"Object Screen: {self.object_screen}, "
                f"Object Order: {self.object_order}, "
                f"Has Style: {self.has_style}, "
                f"Style: {self.style}, "
                f"Expected Answer: {self.expected_answer}, "
                f"Required: {self.required}"
		)

class ClinicQuestionnaire(models.Model):
    clinic = models.ForeignKey(Clinic, related_name='questionnaires', on_delete=models.CASCADE)
    questionnaire = models.ForeignKey(Questionnaire, related_name='clinic_questionnaires', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clinic: {self.clinic}, Questionnaire: {self.questionnaire}"