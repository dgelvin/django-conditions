#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
Exceptions used by conditions
'''

from django.utils.translation import ugettext as _


class NoExistsWhen(Exception):
    '''
    When you subclass ConditionClass, you MUST override exists_when. This
    exception is raised if you don't.
    '''

    def __init__(self):
        raise NotImplementedError(_(u"You must override exists_when in your "
                                    u"proxy ConditionClass"))


class NoRelativeDelta(Exception):
    '''
    The delayed_action and recurring_action MUST be passed a
    dateutils.relativedelta object. This exception is raised if they aren't.
    '''

    def __init__(self, decorator):
        self.decorator = decorator

    def __str__(self):
        return _(u"You must provde a dateutils.relativedelta to any %(dec)s "
                 u"decorator") % {'dec': self.decorator}
