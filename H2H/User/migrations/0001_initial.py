# Generated by Django 5.1.4 on 2025-04-24 05:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Week',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week', models.IntegerField(default=0)),
                ('updated_on_wednesday', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='League',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('draft_date', models.DateTimeField()),
                ('time_per_pick', models.IntegerField(default=60)),
                ('positional_betting', models.BooleanField(default=False)),
                ('max_capacity', models.IntegerField(default=10)),
                ('private', models.BooleanField(default=False)),
                ('join_code', models.CharField(blank=True, max_length=6, null=True, unique=True)),
                ('draftStarted', models.BooleanField(default=False)),
                ('draftComplete', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_leagues', to=settings.AUTH_USER_MODEL)),
                ('users', models.ManyToManyField(blank=True, related_name='joined_leagues', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Draft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_pick', models.IntegerField(default=0)),
                ('draft_order', models.JSONField()),
                ('picks', models.JSONField(default=list)),
                ('league', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='User.league')),
            ],
        ),
        migrations.CreateModel(
            name='Matchup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week', models.IntegerField(default=0)),
                ('team1score', models.DecimalField(decimal_places=2, max_digits=5)),
                ('team2score', models.DecimalField(decimal_places=2, max_digits=5)),
                ('position', models.CharField(blank=True, max_length=50, null=True)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='User.league')),
                ('team1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matchups_as_team1', to=settings.AUTH_USER_MODEL)),
                ('team2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matchups_as_team2', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('link', models.URLField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pictures/')),
                ('currency', models.CharField(default=50.0, max_length=10)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, default='N/A', max_length=100)),
                ('rank', models.IntegerField(default=0)),
                ('wins', models.IntegerField(default=0)),
                ('losses', models.IntegerField(default=0)),
                ('points_for', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)),
                ('points_against', models.DecimalField(decimal_places=2, default=0.0, max_digits=6)),
                ('QB', models.CharField(default='N/A', max_length=20)),
                ('RB1', models.CharField(default='N/A', max_length=20)),
                ('RB2', models.CharField(default='N/A', max_length=20)),
                ('WR1', models.CharField(default='N/A', max_length=20)),
                ('WR2', models.CharField(default='N/A', max_length=20)),
                ('TE', models.CharField(default='N/A', max_length=20)),
                ('FLX', models.CharField(default='N/A', max_length=20)),
                ('K', models.CharField(default='N/A', max_length=20)),
                ('DEF', models.CharField(default='N/A', max_length=20)),
                ('BN1', models.CharField(default='N/A', max_length=20)),
                ('BN2', models.CharField(default='N/A', max_length=20)),
                ('BN3', models.CharField(default='N/A', max_length=20)),
                ('BN4', models.CharField(default='N/A', max_length=20)),
                ('BN5', models.CharField(default='N/A', max_length=20)),
                ('BN6', models.CharField(default='N/A', max_length=20)),
                ('IR1', models.CharField(default='N/A', max_length=20)),
                ('IR2', models.CharField(default='N/A', max_length=20)),
                ('author', models.ForeignKey(default=-1, on_delete=django.db.models.deletion.CASCADE, related_name='ReDraft', to=settings.AUTH_USER_MODEL)),
                ('league', models.ForeignKey(default=-1, on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='User.league')),
            ],
        ),
        migrations.CreateModel(
            name='Bet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_id', models.IntegerField()),
                ('position', models.CharField(max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved', models.BooleanField(default=False)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bets', to='User.league')),
                ('matchup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bets', to='User.matchup')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bets', to='User.team')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_bets', to='User.team')),
            ],
        ),
        migrations.CreateModel(
            name='TradeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender_players', models.JSONField()),
                ('receiver_players', models.JSONField()),
                ('currency_offered', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('currency_requested', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trade_requests', to='User.league')),
                ('receiver_team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_trades', to='User.team')),
                ('sender_team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_trades', to='User.team')),
            ],
        ),
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invited_by', models.ForeignKey(db_column='invited_by_id', on_delete=django.db.models.deletion.CASCADE, related_name='sent_invites', to=settings.AUTH_USER_MODEL)),
                ('invited_user', models.ForeignKey(db_column='invited_user_id', on_delete=django.db.models.deletion.CASCADE, related_name='received_invites', to=settings.AUTH_USER_MODEL)),
                ('league', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='User.league')),
            ],
            options={
                'unique_together': {('league', 'invited_user')},
            },
        ),
    ]
