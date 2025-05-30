from django.db import models

# Create your models here.
class KategoriSoal(models.Model):
    nama = models.CharField(max_length=50,blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama
