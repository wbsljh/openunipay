'''
@summary: This is the main interface that can be used to create order, query order status and process notification 
@author: EricPan(pan.weifeng@live.cn)
@contact: EricPan(pan.weifeng@live.cn)
'''
from django.db import transaction
from openunipay.models import OrderItem, PAY_WAY_WEIXIN, PAY_WAY_ALI
from openunipay.paygateway import weixin, alipay, PayResult
from openunipay import exceptions, logger
from openunipay.util import datetime
from openunipay import business
    
_PAY_GATEWAY = {PAY_WAY_WEIXIN:weixin.WeiXinPayGateway(),
                PAY_WAY_ALI:alipay.AliPayGateway(), }

@transaction.atomic
def create_order(orderno, payway, clientIp, product_desc, product_detail, fee, user=None, attach=None, expire=1440, user_to=None):
    '''
    @summary: create order
    @param orderno: order no
    @param payway: payway
    @param clientIp: IP address of the client that start the pay process
    @param product_desc: short description of the product
    @param product_detail: detail information of the product
    @param fee: price of the product. now, only support RMB. unit: Fen
    @param user: user identify
    @param attach: attach information. must be str
    @param expire: expire in minutes 
    '''
    if not is_supportted_payway(payway):
        raise exceptions.PayWayError()
    
    orderItemObj = OrderItem()
    orderItemObj.orderno = orderno
    orderItemObj.user = user
    orderItemObj.user_to = user_to 
    orderItemObj.product_desc = product_desc
    orderItemObj.product_detail = product_detail
    orderItemObj.fee = fee
    orderItemObj.payway = payway
    orderItemObj.attach = attach
    orderItemObj.initial_orlder(expire)
    orderItemObj.save()
    
    # send order to pay gateway
    gatewayData = _PAY_GATEWAY[payway].create_order(orderItemObj, clientIp)
    logger.info('order created. orderno:{}, payway:{}, clientIp:{}, product:{},fee:{}, gateway data:{}'.format(orderno, payway, clientIp, product_desc, fee, gatewayData))
    return gatewayData

@transaction.atomic
def query_order(orderno):
    '''
    @summary: query status of order
    @param orderno: order no 
    '''
    orderItemObj = OrderItem.objects.get(orderno=orderno)
    if orderItemObj.paied:
        return PayResult(orderItemObj.orderno)
    elif orderItemObj.lapsed:
        return PayResult(orderItemObj.orderno, succ=False, lapsed=True)
    else:
        payResult = _PAY_GATEWAY[orderItemObj.payway].query_order(orderItemObj.orderno)
        _update_order_pay_result(payResult)
        return payResult

@transaction.atomic
def process_notify(payway, requestContent):
    '''
    @summary:  process async notification from pay interface
    @param payway: payway
    @param requestContent:  request body from pay interface
    @return: an instance of PayResult
    '''
    if not is_supportted_payway(payway):
        raise exceptions.PayWayError()
    payResult = _PAY_GATEWAY[payway].process_notify(requestContent)
    _update_order_pay_result(payResult)
    logger.info('process notify. payway:{}, content:{}'.format(payway, requestContent))
    return payResult

def is_supportted_payway(payway):
    return payway in _PAY_GATEWAY


def _update_order_pay_result(payResult):
    if payResult.Succ:
        orderItemObj = OrderItem.objects.get(orderno=payResult.OrderNo)
        orderItemObj.paied = True
        orderItemObj.lapsed = False
        orderItemObj.dt_pay = datetime.local_now()
        orderItemObj.save()
        business.process_business(orderItemObj)
    elif payResult.Lapsed:
        orderItemObj = OrderItem.objects.get(orderno=payResult.OrderNo)
        orderItemObj.paied = False
        orderItemObj.lapsed = True
        orderItemObj.dt_pay = None
        orderItemObj.save()
