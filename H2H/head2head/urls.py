"""
URL configuration for head2head project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from all_players import views

from all_players.scheduler import start_scheduler
from User.views import register_user, VerifyTokenView, UserProfileView, CreateUserView, get_user_info, update_user_info
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('allPlayers/', views.allPlayer),
    path('playerInfo/<int:id>', views.player_info),
    path('api/user/register/', register_user, name='register'),
    path('create-user/', CreateUserView.as_view(), name='create_user'),
    path('user/token', TokenObtainPairView.as_view(), name='get_token'),
    path('user/token/refresh', TokenRefreshView.as_view(), name='refresh'),
    path('user-auth/', include('rest_framework.urls')),
    path('search/', views.search_player, name='search_player'),
    path('api/verifyToken/', VerifyTokenView.as_view(), name='verify_token'),
    path('api/user/profile', UserProfileView.as_view(), name='user-profile'),
    path('api/user/info/', get_user_info, name='get_user_info'),
    path('api/user/update/', update_user_info, name='update_user_info'),
    path('api/topTenPlayers/', views.topTenPlayers, name='top_ten_players'),
]
start_scheduler()