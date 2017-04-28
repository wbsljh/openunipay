"""
business process
"""
import json
import logging
from edu_accounts.models import Course, Activity, Profile, CourseProfileShip, ActivityProfileShip

_logger = logging.getLogger('openunipay_process_business')

def process_business(order_item):
    _logger.info('start process business:{}'.format(order_item))
    attachObj = json.loads(order_item.attach)
    profile = Profile.objects.get(pk=order_item.user)
    if profile.user_type == '0':
        profile.user_type = '1'
        profile.save()
    if attachObj.get('prod_type') == '0':
        prodObj = Course.objects.get(pk=attachObj.get('prod_id')) 
        profile.teachers.add(prodObj.owner) 
        profile.save()
        prodObj.applys_count += 1
        prodObj.save()
        CourseProfileShip.objects.create(profile=profile, course=prodObj)
    if attachObj.get('prod_type') == '1':
        prodObj = Activity.objects.get(pk=attachObj.get('prod_id')) 
        prodObj.applys_count += 1
        prodObj.save()
        ActivityProfileShip.objects.create(profile=profile, activity=prodObj)
