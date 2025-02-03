from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class traditional_redraft(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name = "ReDraft")
    rank = models.IntegerField(default=0)
    QB = models.CharField(max_length=20, default='N/A')
    RB1 = models.CharField(max_length=20,default='N/A')
    RB2 = models.CharField(max_length=20,default='N/A')
    WR1 = models.CharField(max_length=20,default='N/A')
    WR2 = models.CharField(max_length=20,default='N/A')
    TE = models.CharField(max_length=20,default='N/A')
    FLX = models.CharField(max_length=20,default='N/A')
    K = models.CharField(max_length=20,default='N/A')
    DEF = models.CharField(max_length=20,default='N/A')
    BN1 = models.CharField(max_length=20,default='N/A')
    BN2 = models.CharField(max_length=20,default='N/A')
    BN3 = models.CharField(max_length=20,default='N/A')
    BN4 = models.CharField(max_length=20,default='N/A')
    BN5 = models.CharField(max_length=20,default='N/A')
    BN6 = models.CharField(max_length=20,default='N/A')
    IR1 = models.CharField(max_length=20,default='N/A')
    IR2 = models.CharField(max_length=20,default='N/A')

    def __str__(self):
        return f"{self.title} {self.author}"