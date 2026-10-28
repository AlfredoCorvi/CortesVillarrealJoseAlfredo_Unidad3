from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .forms import LoginForm
from . import views

urlpatterns = [
    path('nasa/', views.nasa_gallery, name='nasa_gallery'),
    path('', views.index, name='index'),
    path('registro/', views.register, name='register'),
    path('login/', LoginView.as_view(
        template_name='universe/auth/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
