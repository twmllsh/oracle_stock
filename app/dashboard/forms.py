from django.apps import apps
from django import forms
from .models import *
from django.db.models import Q, Max, Min, Avg
import numpy as np


class StockFilterForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        chartvalue = apps.get_model('dashboard','ChartValue')
        # growth_values
        growth_values = chartvalue.objects.exclude(
            Q(growth_y1__isnull=True) | Q(growth_y1__lte=0)
        ).aggregate(
            min_value=Min('growth_y1'),
            max_value=Max('growth_y1'),
            avg_value=Avg('growth_y1'),
        )

        self.fields['consen_slider'] = forms.IntegerField(
            label='consen_slider', 
            initial=growth_values.get('avg_value', 20),  # 기본값 설정
            min_value=growth_values.get('min_value', 20), 
            max_value=growth_values.get('max_value', 1000),  # 기본값 설정
        )

        # sun_width_values
        sun_width_values = chartvalue.objects.exclude(
            Q(chart_d_sun_width__isnull=True)
        ).aggregate(
            min_value=Min('chart_d_sun_width'),
            max_value=Max('chart_d_sun_width'),
            avg_value=Avg('chart_d_sun_width'),
        )

        self.fields['sun_slider'] = forms.IntegerField(
            label='sun_slider',
            initial=30,
            min_value=sun_width_values.get('min_value', 0),
            max_value=sun_width_values.get('max_value', 500),
        )

        # coke_width_values
        coke_width_values = chartvalue.objects.exclude(
            Q(chart_d_bb240_width__isnull=True)
        ).aggregate(
            min_value=Min('chart_d_bb240_width'),
            max_value=Max('chart_d_bb240_width'),
            avg_value=Avg('chart_d_bb240_width'),
        )

        self.fields['coke_slider'] = forms.IntegerField(
            label='coke_slider',
            initial=60,
            min_value=coke_width_values.get('min_value', 5),
            max_value=coke_width_values.get('max_value', 400),
        )
    
    consen = forms.BooleanField(label='consen', required=False)
    
    turnarround = forms.BooleanField(label='turnarround', required=False)
    new_bra = forms.BooleanField(label='new_bra', required=False)
    w3 = forms.BooleanField(label='w3', required=False)

    sun = forms.BooleanField(label='sun', required=False)
    sun_gcv = forms.BooleanField(label='sun_gcv', required=False)
    sun_slider = forms.IntegerField(label='sun_slider',
                                    initial=30,
                                    min_value=0,
                                    max_value=500,
                                    )
    
    coke = forms.BooleanField(label='coke', required=False)
    coke_gcv = forms.BooleanField(label='coke_gcv', required=False)

    realtime = forms.BooleanField(label='realtime', required=False)