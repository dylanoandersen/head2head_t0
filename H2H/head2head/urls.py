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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from all_players.scheduler import start_scheduler
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from User import views as user_views
from all_players import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('allPlayers/', views.allPlayer),
    path('playerInfo/<int:id>', views.player_info),
    path('playerStats/<int:id>', views.player_stats),
    path('playerNews/<int:id>', views.player_news),
    path('api/user/register/', user_views.register_user, name='register'),
    path('user/token', TokenObtainPairView.as_view(), name='get_token'),
    path('user/token/refresh', TokenRefreshView.as_view(), name='refresh'),
    path('user-auth/', include('rest_framework.urls')),
    path('search/', views.search_player, name='search_player'),
    path('api/verifyToken/', user_views.VerifyTokenView.as_view(), name='verify_token'),
    path('api/user/profile', user_views.UserProfileView.as_view(), name='user-profile'),
    path('api/user/info/', user_views.get_user_info, name='get_user_info'),
    path('api/user/update/', user_views.update_user_info, name='update_user_info'),
    path('api/topTenPlayers/', views.topTenPlayers, name='top_ten_players'),
    path('api/leagues/', user_views.LeagueListCreateView.as_view(), name='league-list-create'),
    path('api/leagues/<int:pk>/', user_views.LeagueDetailView.as_view(), name='league-detail'),
    path('teams/', user_views.TeamListCreateView.as_view(), name='team-list-create'),
    path('teams/<int:pk>/', user_views.TeamDetailView.as_view(), name='team-detail'),
    path('create_league/', user_views.create_league, name='create_league'),
    path('search_leagues/', user_views.search_league, name='search_leagues'),
    path('api/user/register', user_views.CreateUserView.as_view(), name='register'),
]

start_scheduler()

