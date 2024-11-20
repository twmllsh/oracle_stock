# Generated by Django 5.1.1 on 2024-11-20 16:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usa', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ohlcv_usa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Date', models.DateField()),
                ('Open', models.FloatField()),
                ('High', models.FloatField()),
                ('Low', models.FloatField()),
                ('Close', models.FloatField()),
                ('Volume', models.BigIntegerField()),
                ('ticker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='usa.ticker_usa')),
            ],
            options={
                'verbose_name': 'OHLCV_usa',
                'ordering': ['Date'],
                'unique_together': {('ticker', 'Date')},
            },
        ),
    ]
