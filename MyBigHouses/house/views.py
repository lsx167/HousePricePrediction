from django.http import HttpResponse, JsonResponse
from .models import House, HistoryPrice
from django.views.generic import View
from django.db.models import Q
import pickle
from pymongo import MongoClient
import datetime


# url: house/price/<city>/history?last_n_month=xx
class History(View):
    '''历史房价接口'''

    def __init__(self, **kwargs):
        with open("./house/city_mapping_e2c.pkl", "rb") as f:
            self.city_mapping = pickle.load(f)

    def get(self, request, city):
        # 检查是否有该城市
        location = self.city_mapping.get(city, None)
        if location is None:
            return JsonResponse({'code': 1, 'msg': "没有这个城市"})

        # 检查 '最近n月' 是否合法
        try:
            last_n_month = int(float(request.GET.get("last_n_month", 6)))

            if last_n_month <= 0:
                raise ValueError
        except ValueError:
            return JsonResponse({'code': 2, 'msg': "不合法的年份信息"})

        # 查询数据库
        past_prices = HistoryPrice.objects.filter(location=location).order_by("-year", "-month")[:last_n_month]

        count = len(past_prices)  # 检索到的有效记录数
        prices = []
        for price in past_prices[::-1]:  # 数据汇总
            prices.append(['{}-{}'.format(price.year, price.month), str(price.average_price), str(price.tendency)])

        return JsonResponse({"code": 0, "count": count, "city": location, "data": prices})  # 返回 Json 响应

    def post(self):
        pass


# url:house/price/<city>/sub_location/
class CityInfoView(View):
    '''城市层级信息接口'''

    def __init__(self):
        with open("./house/city_mapping_e2c.pkl", "rb") as f:
            self.city_mapping = pickle.load(f)
            # 建立到 MongoDB 的连接
        client = MongoClient(host="42.159.122.43", port=27018)
        db = client.MBH
        self.city_relations = db.city_relations
        # 查询一次，存储在 cursor 中
        self.cursor = list(self.city_relations.find())[0]

    def get(self, request, location):
        # 英文转中文
        location_cn = self.city_mapping.get(location, None)
        if location_cn is None:
            return JsonResponse({"code": 1, "msg": "查询参数有误"})
        # 去数据库查询
        sub_location = self.cursor.get(location_cn, "None")
        # 返回数据
        if sub_location is None:
            return JsonResponse({"code": 2, "msg": "查无此城"})
        else:
            return JsonResponse({"code": 0, "data": sub_location}, safe=False)


# url:house/price/<city>/sub_location?last_n_month=n
class SubLocationPriceView(View):
    '''获取下级最新房价'''

    def __init__(self):
        with open("./house/city_mapping_e2c.pkl", "rb") as f:
            self.city_mapping = pickle.load(f)
            # 建立到 MongoDB 的连接
        client = MongoClient(host="42.159.122.43", port=27018)
        db = client.MBH
        self.city_relations = db.city_relations
        # 查询一次，存储在 cursor 中
        self.cursor = list(self.city_relations.find())[0]

    def get(self, request, city_name):
        location_cn = self.city_mapping.get(city_name, None)
        last_month = int(request.GET.get('last_n_month', 1))
        if location_cn is None:
            return JsonResponse({"code": 1, "msg": "没有这个城市"})

        subs = self.cursor.get(location_cn, None)
        if subs is None:
            return JsonResponse({"code": 2, "msg": "已经到最后一级了"})
        ret = [list() for i in range(last_month)]
        date_time = list()
        print(datetime.datetime.now())
        for i, sub in enumerate(subs):
            sub_info = HistoryPrice.objects.filter(location=sub).order_by("-year", "-month")[:last_month] # 只要最近 last_month 个月
            if len(list(sub_info)) == 0:
                continue
            else:
                for index in range(last_month):
                    ret[index].append([sub_info[index].location, sub_info[index].average_price])
                    if i == 0:
                        date_time.append('{}-{}'.format(sub_info[index].year, sub_info[index].month))
        print(datetime.datetime.now())
        return JsonResponse({"code": 0, "data": ret, "location_cn": location_cn, "time": date_time})
