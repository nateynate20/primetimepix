<<<<<<< HEAD
# primetimepix/models.py
from django.db import models
from django.contrib.auth.models import User
=======
# primetimepix/models.py
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913


<<<<<<< HEAD
    def __str__(self):
        return self.username


class LeagueCreationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='league_creation_requests')
    league_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.league_name} requested by {self.user.username}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "League Creation Request"
        verbose_name_plural = "League Creation Requests"

=======
>>>>>>> 80abcf7c5cfbf6c12ebf84c535599e472ccfb913