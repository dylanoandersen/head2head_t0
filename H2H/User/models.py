from django.db import models
from django.contrib.auth.models import User
import uuid



# Create your models here.





class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    link = models.URLField(null=True, blank=True)  # Optional link for the notification
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"


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
    time_per_pick = models.IntegerField(default=60)
    positional_betting = models.BooleanField(default=False)
    max_capacity = models.IntegerField(default=10)  # Default max number of users
    private = models.BooleanField(default=False)  # True = Private, False = Public
    join_code = models.CharField(max_length=6, unique=True, blank=True, null=True)  # Code for private leagues
    users = models.ManyToManyField(User, related_name="joined_leagues", blank=True)  # Users in the league
    draftStarted = models.BooleanField(default=False)  # Add this line
    draftComplete = models.BooleanField(default=False)  # New field

    def save(self, *args, **kwargs):
        if self.private and not self.join_code:
            self.join_code = str(uuid.uuid4())[:10]  # Generate a random 10-character code for private leagues
        super().save(*args, **kwargs)

        if self.owner not in self.users.all():
            self.users.add(self.owner)

    def __str__(self):
        return f"{self.name} - {'Private' if self.private else 'Public'}"

class Invite(models.Model):
    league = models.ForeignKey('User.League', on_delete=models.CASCADE, related_name="invites")
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_invites", db_column='invited_user_id')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invites", db_column='invited_by_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('league', 'invited_user')

    def __str__(self):
        return f"Invite to {self.league.name} for {self.invited_user.username} by {self.invited_by.username}"


class Team(models.Model):
    title = models.CharField(max_length=100, default='N/A', blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ReDraft", default=-1)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="teams", default=-1)
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

class Draft(models.Model):
    league = models.OneToOneField(League, on_delete=models.CASCADE)
    current_pick = models.IntegerField(default=0)  # Track the current pick index
    draft_order = models.JSONField()  # List of user IDs in draft order
    picks = models.JSONField(default=list)  # List of picks made

    def get_next_pick(self):
        # Determine the next user in the snake draft order
        total_users = len(self.draft_order)
        round_number = self.current_pick // total_users
        index_in_round = self.current_pick % total_users

        # Reverse the order every other round for the snake pattern
        if round_number % 2 == 1:
            index_in_round = total_users - 1 - index_in_round

        return self.draft_order[index_in_round]

class Matchup(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    week = models.IntegerField(default=0)
    
    team1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='matchups_as_team1'
    )
    team2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='matchups_as_team2'
    )
    
    team1score = models.DecimalField(max_digits=5, decimal_places=2)
    team2score = models.DecimalField(max_digits=5, decimal_places=2)

class Week(models.Model):
    week = models.IntegerField(default=0)