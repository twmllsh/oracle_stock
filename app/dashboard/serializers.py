from rest_framework import serializers
from .models import *

class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = '__all__'

class InfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Info
        fields = '__all__'

class OhlcvSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ohlcv
        fields = '__all__'
        
class FinstatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finstats
        fields = '__all__'
        
class InvestorTradingSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorTrading
        fields = '__all__'

class BrokerTradingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerTrading
        fields = '__all__'

class ChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeLog
        fields = '__all__'

class IssSerializer(serializers.ModelSerializer):
    class Meta:
        model = Iss
        fields = '__all__'

class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = '__all__'
        
class ThemeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeDetail
        fields = '__all__'
        
class UpjongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upjong
        fields = '__all__'

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = '__all__'
        
class ChartValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartValue
        fields = '__all__'
        

