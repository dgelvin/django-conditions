#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
This file contains managers used for conditions.
'''
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .exceptions import NoExistsWhen


class ConditionManager(models.Manager):
    '''
    Manager used by the concrete Condition model in conditions.models.
    '''

    def open_conditions(self):
        '''
        Returns a queryset of 'open' conditions. Conditions are open if their
        ended is null. This is called like:
            Condition.objects.open_conditions()
        '''
        return super(ConditionManager, self).get_query_set() \
                                            .filter(ended__isnull=True)


class ConditionClassManager(models.Manager):
    '''
    Manager used to replace 'objects' in any class that subclasses
    ConditionClass.
    '''

    def get_query_set(self):
        '''
        Returns a query set filtered by the subclasses .exists_when atrribute
        For example, if your condition subclass has:
            exists_when = Q(color='blue')

        Then when you call:
            YourCondition.objects.all()

        You will get only objects for which color == 'blue'
        '''
        try:
            return super(ConditionClassManager, self) \
                                                .get_query_set() \
                                                .filter(self.model.exists_when)
        except AttributeError:
            raise NoExistsWhen

    def _get_ids_with_conditions(self):
        '''
        Returns a list of integers of all of the Condition object_ids
        for conditions that are open and have a content_type equal to the
        class that was used to call this manager.

        So in other words, if our condition class is MyCondition, this
        function will return an integer list of all of the primary keys
        of MyCondition objects that are currently recognized as being 'open'
        in the database.

        This is used by the methods below to find conditions that need to be
        opened or closed.
        '''
        from .models import Condition
        return Condition.objects \
                        .open_conditions() \
                        .filter(content_type=self.model.get_ct()) \
                        .values_list('object_id', flat=True)

    def to_be_created(self):
        '''
        Returns a query set of all the objects in self.model.objects
        for which exists_when is true, but there isn't an open Condition object
        for it yet.
        '''
        return self.get_query_set() \
                   .exclude(pk__in=self._get_ids_with_conditions())

    def to_be_ended(self):
        '''
        Returns a query set of all the objects in self.model.objects
        for which exists_when is false, but there is an open condition for it.
        '''
        try:
            qs = super(ConditionClassManager, self) \
                                            .get_query_set() \
                                            .exclude(self.model.exists_when)
        except AttributeError:
            raise NoExistsWhen

        return qs.filter(pk__in=self._get_ids_with_conditions())
