# Generated by Django 5.1.1 on 2024-11-26 06:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_chartvalue_eps_chartvalue_매물대1_chartvalue_매물대2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chartvalue',
            name='pre_vol',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chartvalue',
            name='vol20',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
