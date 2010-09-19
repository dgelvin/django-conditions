#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
Provides the processconditions command to ./manage

Optionally takes an app name, or it will process any models that subclass
ConditionClass in every app.

Processing consists of:
    1.  Create Condition objects for any model in a ConditionClass subclass
        that doesn't already exist and is open.  Execute initial_actions for
        those models.

    2.  Set the 'ended' DateTimeField on any Conditions that exist, but don't
        aren't in the 'exists_when' query of the ConditionClass subclass.
        execute the ending_actions for those models.

    3.  Loop through and execute all triggered delayed / recurring actions

Takes two optional arguments:

    --all: Explicitly process all apps (default behavior)
    --no-execute: Create / end Condition objects, but don't execute any actions
'''

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from django.conf import settings

from ...models import ConditionClass


class Command(BaseCommand):
    '''
    Django command extension, provides ./manage processconditions
    '''


    args = '[appname] [--all] [--no-execute]'
    help = _(u"Process conditions for apps")

    option_list = BaseCommand.option_list + (
        make_option('--all',
            action='store_true',
            dest='all_apps',
            default=False,
            help=_(u"Process conditions for all apps")),

        make_option('--no-execute',
            action='store_true',
            dest='no_execute',
            default=False,
            help=_(u"Don't execute any actions")),
    )

    def handle(self, app=None, *args, **options):
        '''
        Main handle method that will be called
        '''
        if options.get('all_apps', False):
            target = app
            app = None

        if options.get('no_execute', False):
            execute = False
        else:
            execute = True

        for cls in self.condition_classes(app):
            cls.create_all_conditions(execute=execute)
            cls.end_all_conditions(execute=execute)

            if execute:
                cls.execute_all_delayed()
                cls.execute_all_recurring()

    def condition_classes(self, app=None):
        '''
        Return all classes that subclass ConditionClass in app, or if app
        is None, in all apps.
        '''
        condition_classes = ConditionClass.__subclasses__()

        if app:
            if not app in settings.INSTALLED_APPS:
                raise CommandError(_(u"No app named %(app)s in " \
                                     u"INSTALLED_APPS") % {'app': app})

            condition_classes = filter(lambda x: x._meta.app_label == app,
                          condition_classes)

            if len(condition_classes) == 0:
                raise CommandError(_(u"%(app)s does not have any "
                                     u"conditions") % {'app': app})

        if len(condition_classes) == 0:
            raise CommandError(_(u"No conditions found in any of your " \
                                 u"INSTALLED_APPS"))


        return condition_classes
