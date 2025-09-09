# primetimepix/models.py
from django.db import models

class PrimetimePixBaseModel(models.Model):
    """Base model with common fields for all app models"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# Remove the Player model - it's handled in apps.users.models as Profile