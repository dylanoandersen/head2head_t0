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
from all_players.views import LeagueListCreateView, LeagueDetailView, TeamListCreateView, TeamDetailView
from User import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('allPlayers/', views.allPlayer),
    path('playerInfo/<int:id>', views.player_info),
    path('api/user/register/', user_views.register_user, name='register'),
    path('create-user/', user_views.CreateUserView.as_view(), name='create_user'),
    path('user/token', TokenObtainPairView.as_view(), name='get_token'),
    path('user/token/refresh', TokenRefreshView.as_view(), name='refresh'),
    path('user-auth/', include('rest_framework.urls')),
    path('search/', views.search_player, name='search_player'),
    path('api/verifyToken/', VerifyTokenView.as_view(), name='verify_token'),
    path('api/leagues/', LeagueListCreateView.as_view(), name='league-list-create'),
    path('api/leagues/<int:pk>/', LeagueDetailView.as_view(), name='league-detail'),
    path('teams/', TeamListCreateView.as_view(), name='team-list-create'),
    path('teams/<int:pk>/', TeamDetailView.as_view(), name='team-detail'),
    path('create_league/', views.create_league, name='create_league'),
    path('search_leagues/', views.search_league, name='search_leagues'),

]
#start_scheduler()