from django.apps import apps
from django import forms
from .models import *
from django.db.models import Q, Max, Min, Avg
import numpy as np


class StockFilterForm(forms.Form):
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
        
    #     chartvalue = apps.get_model('dashboard','ChartValue')
    #     # growth_values
    
    consen = forms.BooleanField(label='consen', required=False)
    consen_slider = forms.IntegerField(label='consen_slider',
                                    initial=30,
                                    min_value=0,
                                    max_value=500,
                                    )
    
    
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
    coke_slider = forms.IntegerField(label='coke_slider',
                                    initial=30,
                                    min_value=0,
                                    max_value=500,
                                    )
    
    
    realtime = forms.BooleanField(label='realtime', required=False)
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        # min과 max 값 설정
        sun_width_dict = self.calculate_sun_min_max_value()
        self.fields['sun_slider'].widget.attrs['min'] = sun_width_dict['min_value']
        self.fields['sun_slider'].widget.attrs['max'] = sun_width_dict['max_value']

        # min과 max 값 설정
        coke_width_dict = self.calculate_coke_min_max_value()
        self.fields['coke_slider'].widget.attrs['min'] = coke_width_dict['min_value']
        self.fields['coke_slider'].widget.attrs['max'] = coke_width_dict['max_value']
        
        consen_dict = self.calculate_consen_min_max_value()
        self.fields['consen_slider'].widget.attrs['min'] = consen_dict['min_value']
        self.fields['consen_slider'].widget.attrs['max'] = consen_dict['max_value']

    ## 함수에 nan값이 있다. 수치값만 나오게 필터를 잘하던 데이터베이스 값넣을대 ..변경해야함.
    def calculate_sun_min_max_value(self):
        sun_width_values = ChartValue.objects.exclude(
                Q(chart_d_sun_width__isnull=True)
            ).aggregate(
                min_value=Min('chart_d_sun_width'),
                max_value=Max('chart_d_sun_width'),
            )
        return sun_width_values
    
    
    def calculate_consen_min_max_value(self):
        growth_values = ChartValue.objects.filter(
            Q(growth_y1__isnull=False) | Q(growth_y1__gte=0)
        ).aggregate(
            min_value=Min('growth_y1'),
            max_value=Max('growth_y1'),
        )
        return growth_values
    
    def calculate_coke_min_max_value(self):
        coke_width_values = ChartValue.objects.exclude(
            Q(chart_d_bb240_width__isnull=True)
        ).aggregate(
            min_value=Min('chart_d_bb240_width'),
            max_value=Max('chart_d_bb240_width'),
            # avg_value=Avg('chart_d_bb240_width'),
        )
        return coke_width_values
  

        
