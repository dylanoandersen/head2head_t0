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
            name='traditional_redraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('rank', models.IntegerField(default=0)),
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
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ReDraft', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
