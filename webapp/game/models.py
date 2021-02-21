from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=30)
    host = models.ForeignKey(User, default=None, on_delete=models.PROTECT)
    player = models.ForeignKey(User, default=None, null=True, on_delete=models.PROTECT, related_name='player')
    num_player = models.IntegerField()

class Profile(models.Model):
    """
    class for user profile:
        user: built-in model from django
        bio: user bio, max_length = 100
        picture: user picture
        num_win: # of games user win, default 0
        num_lose: # of games user loses, default 0
        score: the current score of user, default 0
        friends: friends of the user
        invitation: invitations received by the user
    """
    GENDER = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female')
    ]

    user = models.OneToOneField(User, default=None, on_delete=models.PROTECT, related_name="my_profile")
    bio = models.CharField(default='', max_length=100)
    gender = models.CharField(choices=GENDER, max_length=10)
    picture = models.FileField(upload_to='profile-images', blank=True)
    content_type = models.CharField(max_length=50)
    num_win = models.IntegerField(default=0)
    num_lose = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    friends = models.ManyToManyField(User, blank=True)
    invitations = models.ManyToManyField(User, blank=True, related_name='invitations')

