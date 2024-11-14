from django.contrib import admin
from .models import *
# Register your models here.


class TickerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", '구분')


class InfoAdmin(admin.ModelAdmin):
    list_display = ("ticker", "액면가", '상장주식수', '외국인소진율',
                    'EPS', 'ROE', '배당수익율', 'PER_12M', '동일업종저per_name')

    # search_fields = ('ticker')
    
    # 필터링할 필드
    # list_filter = ('EPS','PER_12M','배당수익율')

class FinstatsAdmin(admin.ModelAdmin):
    list_display = ("ticker", '매출액', "영업이익", '당기순이익', '유보율', '부채비율',
                    'EPS', 'ROE', '배당수익률', 'PER')

    # list_filter = ('fintype', 'year', 'quarter')
    pass

    
admin.site.register(Ticker,TickerAdmin)
admin.site.register(Info, InfoAdmin)
admin.site.register(Finstats, FinstatsAdmin)



