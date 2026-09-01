from django.db import models
from django.contrib.auth.models import User
from tenants.models import Tenant
# Create your models here.


class Membership(models.Model):
    user=models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )


    tenant=models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE
    )


    Role_choices=[
        ("ADMIN","Admin"),
        ("EDITOR","Editor"),
        ("VIEWER","Viewer"),
    ]
    role=models.CharField(max_length=100,choices=Role_choices,default="VIEWER")

    class Meta:
        unique_together=['user','tenant']
        

    def __str__(self):
        return f'{self.user.username} - {self.tenant.name}'