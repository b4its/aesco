from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.models import User  
from django.contrib.auth import login, logout, authenticate

# Login view
def loginView(request):
    if request.user.is_authenticated:
        return redirect('home')  # jika sudah login, arahkan ke halaman home
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.info(request, 'Selamat Datang ' + str(request.user) + '!')  # Pesan Selamat datang
            return redirect('home')  # Arahkan ke halaman home setelah login berhasil
        else:
            messages.error(request, 'Username atau password kamu salah!')  # Pesan error jika login gagal
    
    return render(request, 'login.html')  # Tampilkan halaman login

# Register view
def registerView(request):
    if request.user.is_authenticated:
        return redirect('home')  # jika sudah login, arahkan ke halaman home
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        # Cek apakah password dan konfirmasi password cocok
        if password != password2:
            messages.error(request, "Password dan konfirmasi password tidak cocok!")
            return redirect('registrationApps')

        # Cek apakah username sudah digunakan
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('registrationApps')

        # Cek apakah email sudah digunakan
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email sudah digunakan!")
            return redirect('registrationApps')

        # Jika tidak ada masalah, buat user baru
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect('loginApps')  # Arahkan ke halaman login setelah registrasi berhasil
    
    return render(request, 'register.html')  # Tampilkan halaman registrasi

# Logout view
def custom_logout(request):
    logout(request)  # Logout pengguna
    messages.success(request, "Anda telah berhasil logout!")  # Pesan logout sukses
    return redirect('loginApps')  # Arahkan ke halaman login setelah logout
