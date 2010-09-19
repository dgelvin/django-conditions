#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
Admin registrations for conditions
'''
from django.contrib import admin

from .models import Condition, Action

admin.site.register(Condition)
admin.site.register(Action)
