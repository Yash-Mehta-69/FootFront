from django.db import models
from django.conf import settings

# --- Vendor Model ---
class Vendor(models.Model):
    # Foreign Key references user table 
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    shopName = models.CharField(max_length=30, unique=True)
    shopAddress = models.CharField(max_length=500)
    business_phone = models.CharField(max_length=10)
    description = models.CharField(max_length=1000, blank=True, null=True)
    panCard = models.ImageField(upload_to='vendors/pan_cards/')
    adharCard = models.ImageField(upload_to='vendors/adhar_cards/')
    is_blocked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.shopName