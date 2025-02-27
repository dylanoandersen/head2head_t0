from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class traditional_redraft(models.Model):  # Class names should be in PascalCase

    title = models.CharField(max_length=100)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ReDraft")
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

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)

    def __str__(self):
        return self.user.username
    


class League(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_leagues")
    draft_date = models.DateTimeField()
    time_per_pick = models.IntegerField(default=60)  # In seconds
    positional_betting = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=255)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_teams")
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="teams")
    football_players = models.JSONField(default=list)  # Store player IDs in a list

    def __str__(self):
        return f"{self.name} ({self.owner.display_name}'s team in {self.league.name})"