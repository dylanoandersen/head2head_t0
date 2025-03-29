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
    path('api/search_player/', views.search_player, name='search_player'),
    path('user/token', TokenObtainPairView.as_view(), name='get_token'),
    path('user/token/refresh', TokenRefreshView.as_view(), name='refresh'),
    path('user-auth/', include('rest_framework.urls')),
    path('search/', views.search_player, name='search_player'),
    path('api/verifyToken/', user_views.VerifyTokenView.as_view(), name='verify_token'),
    path('api/user/profile', user_views.UserProfileView.as_view(), name='user-profile'),
    path('api/user/info/', user_views.get_user_info, name='get_user_info'),
    path('api/user/update/', user_views.update_user_info, name='update_user_info'),
    path('api/user/<int:user_id>/', user_views.get_user_by_id, name='get_user_by_id'),
    path('api/topTenPlayers/', views.topTenPlayers, name='top_ten_players'),
    path('api/leagues/league/<int:league_id>/start_draft/', user_views.start_draft, name='start_draft'),
    path('api/league/<int:league_id>/check_membership/', user_views.check_league_membership, name='check_membership'),
    path('api/league/<int:league_id>/check_draft_status/', user_views.check_draft_status, name='check_draft_status'),
    path('api/league/<int:league_id>/verify_current_pick_user/', user_views.verify_current_pick_user, name='verify_current_pick_user'),
    path('api/leagues/<int:league_id>/update_settings/', user_views.update_league_settings, name='update-settings'),
    path('api/leagues/<int:league_id>/leave/', user_views.leave_league, name='leave-league'),
    path('api/leagues/<int:league_id>/delete/', user_views.delete_league, name='delete-league'),
    path('api/leagues/', user_views.LeagueListCreateView.as_view(), name='league-list-create'),
    path('api/leagues/<int:pk>/', user_views.LeagueDetailView.as_view(), name='league-detail'),
    path('api/teams/', user_views.TeamListCreateView.as_view(), name='team-list-create'),
    path('api/teams/<int:pk>/', user_views.TeamDetailView.as_view(), name='team-detail'),
    path('api/leagues/search/', user_views.search_league, name='search_league'),
    path('api/leagues/create/', user_views.create_league, name='create_league'),
    path('api/leagues/join/public/<int:league_id>/', user_views.join_public_league, name='join-public-league'),
    path('api/leagues/join/private/', user_views.join_private_league, name='join-private-league'),
    path('api/leagues/myleagues/', user_views.my_leagues, name='my-leagues'),
    path('api/leagues/check_join_code/<str:join_code>/', user_views.check_join_code, name='check-join-code'),

]

start_scheduler()

