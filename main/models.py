from django.db import models

# Create your models here.
class KategoriSoal(models.Model):
    nama = models.CharField(max_length=50,blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama

class Soal(models.Model):
    kategoriSoal = models.ForeignKey(KategoriSoal, on_delete = models.CASCADE,related_name = 'katSoal')
    nama = models.CharField(max_length=50,blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama

class JawabanSoal(models.Model):
    soal = models.ForeignKey(Soal, on_delete = models.CASCADE,related_name = 'soal')  
    kunci = models.CharField(max_length=50,blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.kunci