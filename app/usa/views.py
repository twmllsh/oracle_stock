from django.shortcuts import render
import pandas as pd

# Create your views here.

def dashboard_usa(request):
    
    
    data = [{ "code":'005930',
            "name":'삼성전자',
            "reasons":'new_bra 3w sun',
            },
            { "code":'000660',
            "name":'sk하이닉스',
            "reasons":'new_bra 3',
            },
            { "code":'310210',
            "name":'보로노이',
            "reasons":'3w',
            },
            ]
    df = pd.DataFrame(data)

    
    condition = request.GET.getlist('condition')
    if condition:
        # df filtering
        pass
    
    context ={}
    context['items'] = df.to_dict('records')
    
    return render(request, 'usa/dashboard.html',context=context)

def item_detail(request, item_code):
    context = {
        'item_code': item_code
    }
    return render(request, 'usa/detail.html',context=context )
