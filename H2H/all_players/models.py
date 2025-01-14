from django.db import models

class Player(models.Model):
    id = models.CharField(max_length=20, primary_key=True) 
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    weight = models.FloatField(default=0)
    displayHeight = models.CharField(default=0, max_length=100)
    age = models.IntegerField(default=0)
    experience = models.CharField(max_length=100, default='0')
    jersey = models.IntegerField(default=-1)


