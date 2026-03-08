from django.db import models
from django.utils import timezone

class sentMessages(models.Model):
    MessageType = (
       ('EMAIL','email'),
       ('SMS','SMS/Text Message'),
    )
    SentStatus = (
       ('SUCCESS','message sent'),
       ('FAIL','message not sent'),
    )
    userid = models.CharField(('user id'),max_length=255)
    msg_type = models.CharField(('message type'), choices=MessageType,max_length=10, blank=True)
    sender = models.CharField(('sender string'),max_length=255)
    destinatary = models.CharField(('destinatary string'),max_length=255)
    sent_date = models.DateTimeField(default=timezone.now , blank=True)
    status = models.CharField(('message status'), choices=SentStatus,max_length=10, blank=True , default='FAIL')
    registered = models.BooleanField('registered', default=False , blank=True)
