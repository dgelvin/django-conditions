#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
This file contains the four decorators that can be used in models subclassing
ConditionClass to define condition actions.

Each decorator injects a _action_type attribute into the function class.
This is later used to introspect the methods of any condition classes
to identifiy action methods.

Additionally, the delayed_action and recurring_action decorators accept
a single dateutils.relativedelta argument that are stored in the function's
_action_delay and _action_interval attributes respectively.
'''

from functools import wraps
from dateutil.relativedelta import relativedelta

from django.utils.translation import ugettext as _

from .exceptions import NoRelativeDelta


def initial_action(func):
    '''
    Decorator used to indentify initial action methods. Does not take any
    arguments. Methods tagged with this decorator will be executed when
    a condition is created.
    '''
    func._action_type = 'initial'

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(*args, **kwargs)
    return func


def delayed_action(delay):
    '''
    Decorator used to indentify delayed action methods. Must be passed a single
    dateutils.relativedelta argument. Methods tagged with this decorator
    will be triggered for execution when the current time is greater than the
    delay time plus the condition.created time. They will only be executed
    once and they will not be triggered for execution if the condition ceases
    to exist before the delay has passed.
    '''
    if not isinstance(delay, relativedelta):
        raise NoRelativeDelta('delayed_action')

    def outer_wrapper(func):
        func._action_type = 'delayed'
        func._action_delay = delay

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(*args, **kwargs)
        return func
    return outer_wrapper


def recurring_action(interval):
    '''
    Decorator used to indentify recurring action methods. Must be passed a
    single dateutils.relativedelta argument. Methods tagged with this decorator
    will be triggered for execution repeatedly, after every interval, as
    long as the condition exists. recurring_action methods are NOT executed
    on condition creation. Their first execution will be at condition.created
    plus the interval.
    '''
    if not isinstance(interval, relativedelta):
        raise NoRelativeDelta('recurring_action')

    def outer_wrapper(func):
        func._action_type = 'recurring'
        func._action_interval = interval

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(*args, **kwargs)
        return func
    return outer_wrapper


def ending_action(func):
    '''
    Decorator used to indentify ending action methods. Does not take any
    arguments.  Methods tagged with this decorator will be executed when
    a condition ends.
    '''
    func._action_type = 'ending'

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(*args, **kwargs)
    return func
