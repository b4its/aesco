from django.urls import path

from .import views

urlpatterns = [
    path('',views.home,name="home"),
    path('proses/pembandinganJawaban',views.pembandinganJawaban,name="pembandinganJawaban"),
    path('kesimpulan', views.kesimpulanViews, name="kesimpulanViews")
]
