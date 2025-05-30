from django.urls import path
from django.contrib.auth.views import LogoutView

from .import views

urlpatterns = [
    path('',views.loginView,name="loginApps"),
    path('accounts/register',views.registerView,name="registrationApps"),
    path('logout/', views.custom_logout, name="logout"),
]
