from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.models import User  
from django.contrib.auth import login, logout, authenticate

def loginView(request):
    if request.user.is_authenticated:
        return redirect('home') 
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.info(request, 'Selamat Datang ' + str(request.user) + '!')
            return redirect('home')  
        else:
            messages.error(request, 'Username atau password kamu salah!')
    
    return render(request, 'login.html')

def registerView(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Password dan konfirmasi password tidak cocok!")
            return redirect('registrationApps')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('registrationApps')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email sudah digunakan!")
            return redirect('registrationApps')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect('loginApps')  
    
    return render(request, 'register.html')

def custom_logout(request):
    logout(request) 
    return redirect('loginApps')  
