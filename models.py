#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 coding=utf-8
'''
Models for conditions. There are two real models (Condition and Action) and
and ConditionClass, an abstract model to be inhereted by other apps that
want to add a condition to one of their models
'''

from datetime import datetime
from inspect import getmembers, ismethod

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

from .managers import ConditionManager, ConditionClassManager


class Condition(models.Model):
    '''
    Concrete condition model. This is used to know what conditions need
    to be opened, or closed, and when they were created or closed.

    It has a generic relation that will be set to the condition proxy class
    of the model that has a condition.
    '''

    class Meta:
        verbose_name = _(u"condition")
        verbose_name_plural = _(u"conditions")

    created = models.DateTimeField(_(u"created"), default=datetime.now,
                            help_text=_(u"When this condition was created"))

    ended = models.DateTimeField(_(u"ended"), blank=True, null=True,
                            help_text=_(u"When this condition ended"))

    '''
    Important: this generic relation will be set to the content type of the
    _proxy_ class of any apps model that extends ConditionClass. So for
    example, if I have a model called Item and a condition subclass for it
    called ItemIsLate, this content_type will be itemislate, _not_ item.
    '''
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    objects = ConditionManager()

    def __unicode__(self):
        return "%s: %s" % (self.content_type.name.title(), self.content_object)


class Action(models.Model):
    '''
    Model used to record actions that have been executed for each condition.
    '''

    class Meta:
        verbose_name = _(u"action")
        verbose_name_plural = _(u"actions")
        get_latest_by = 'executed'

    INITIAL = 'I'
    DELAYED = 'D'
    RECURRING = 'R'
    ENDING = 'E'

    TYPE_CHOICES = (
    (INITIAL, _(u"Initial")),
    (DELAYED, _(u"Delayed")),
    (RECURRING, _(u"Recurring")),
    (ENDING, _(u"Ending")))

    executed = models.DateTimeField(_(u"executed on"), default=datetime.now,
                            help_text=_(u"When the action was executed"))

    '''
    Important: Because we use the name of the method to store what has or has
    not been executed, don't change the name of any of your action methods that
    are already in use, as we may think it was never executed, and execute
    it again.
    '''
    name = models.CharField(_(u"name"), max_length=100,
                            help_text=_(u"Name of the method " \
                                        u" that was executed"))

    condition = models.ForeignKey(Condition, verbose_name=_(u"condition"))

    action_type = models.CharField(_(u"action type"), max_length=1,
                                   choices=TYPE_CHOICES)

    def __unicode__(self):
        return "%s [%s] %s" % (self.condition,
                               self.get_action_type_display(),
                               self.name)


class ConditionClass(models.Model):
    '''
    Abstract class to be inhereted by another app to add condition abilities
    to one of their models.

    Important: This must be inhereted _before_ their concrete class is
    inhereted.  So for example, if I have a concrete class named Item and
    want to create an ItemIsLate condition, this is how to define ItemIsLate:

        from conditions.models import ConditionClass
        class ItemIsLate(ConditionClass, Item):
            class Meta:
                proxy = True

    ConditionClass _must_ be before your concrete model class name, and you
    _must_ set proxy = True in the Meta clas.

    Additionally, you must set the 'exists_when' attribute of the class to
    a set of Q objects used to determine when the condition exists.
    '''

    class Meta:
        abstract = True

    objects = ConditionClassManager()

    @classmethod
    def get_ct(cls):
        '''
        Returns the ContentType for this class.

        Important: ContentType.objects.get_for_model() automatically climbs
        up proxy classes to return the ContentType of the parent. I don't
        know why it does this, because proxy classes _do_ have content types.

        To get the content type of the proxy (which is what we need) and not
        the parent, we use .get_by_natural_key(app_label, name) which doesn't
        climb to the parent.
        '''
        return ContentType.objects \
                          .get_by_natural_key(cls._meta.app_label,
                                              cls._meta.object_name.lower())

    @classmethod
    def _get_action_methods(cls, action_type):
        '''
        Uses inspect.getmembers() to introspect all of the methods of this
        class, and returns a list of all methods (unbound) that have the
        _action_type attribute. These are the methods that have been tagged
        with the various action decorators, as those decorators inject
        _action_type into the function class.
        '''
        retr_list = []
        inspect_lambda = lambda x: ismethod(x) and \
                                   hasattr(x, '_action_type')
        for item in getmembers(cls, inspect_lambda):
            if item[1]._action_type == action_type:
                retr_list.append(item[1])
        return retr_list

    @classmethod
    def create_all_conditions(cls, execute=True):
        '''
        Get the cls.objects.to_be_created() query set, which will contain all
        of the objects of cls condition subclass for which the concrete
        Condition object has not been created (and so we assume the initial
        actions haven't been executed). Loop through those objects and
        create the condition objects, and execute the initial actions (if
        execute == True)
        '''
        for model in cls.objects.to_be_created():
            model.create_condition(execute=execute)

    @classmethod
    def execute_all_delayed(cls):
        '''
        Loop through all of the conditions of cls and check for any delayed
        actions that are triggered, and execute them.
        '''
        for model in cls.objects.all():
            model.execute_delayed_actions()

    @classmethod
    def execute_all_recurring(cls):
        '''
        Loop through all of the conditions of cls and check for any recurring
        actions that are triggered, and execute them.
        '''
        for model in cls.objects.all():
            model.execute_recurring_actions()

    @classmethod
    def end_all_conditions(cls, execute=True):
        '''
        Get the cls.objects.to_be_ended() query set, which will contain
        all of the objects of the _parent_ class to this cls, (and which are
        not in this cls becaue .exists_when == False for them) and for which
        there are still Conditions open (ended is null).  Close them by
        setting condtion.ended = now, then execute the ending actions (if
        execute == True)
        '''
        for model in cls.objects.to_be_ended():
            model.end_condition(execute=execute)

    def get_or_create_condition(self):
        '''
        Get or create the condition for self condition subclass object. Note,
        this will create a new condition even if there is an existing (but
        closed) condition already. This allows conditions to reoccur for the
        same object. (think pregnancy- one woman can have the condition of
        pregnant multiple times)

        We set up the condition property so we can just call:
            self.condition
        And the condition will be created (if it doesn't already exist).

        Just be careful, self.condition will require the database, so if you
        do:
            self.condition.created = some_time
            self.condtion.save()
        It _won't_ actually save the created field.  You need to do:
            condition = self.condition
            condition.create = some_time
            condition.save()
        '''
        condition, c = Condition.objects \
                                .open_conditions() \
                                .get_or_create(content_type=self.get_ct(),
                                               object_id=self.pk)
        return condition
    condition = property(get_or_create_condition)

    def create_condition(self, execute=True):
        '''
        Create the Condition object and, if execute==True, execute all initial
        actions.
        '''
        condition = self.condition
        if execute:
            self.execute_initial_actions()

    def execute_initial_actions(self):
        '''
        Execute all methods for this object tagged with inital_action
        '''
        for action in self._get_action_methods('initial'):
            Action.objects.create(condition=self.condition,
                                  action_type=Action.INITIAL,
                                  name=action.__name__)
            action(self)

    def get_triggered_delayed_actions(self):
        '''
        Return a list of unbound methods that are tagged with delayed_action
        and for which the delay time has passed since the creation of the
        condition.
        '''
        condition = self.condition
        triggered_actions = []
        for action in self._get_action_methods('delayed'):
            qry = Action.objects.filter(condition=condition,
                                        name=action.__name__,
                                        action_type=Action.DELAYED)
            if not qry.count() and \
               datetime.now() >= condition.created + action._action_delay:
                triggered_actions.append(action)
        return triggered_actions

    def execute_delayed_actions(self):
        '''
        Execute all delayed_action methods that are triggered for execution.
        '''
        for action in self.get_triggered_delayed_actions():
            Action.objects.create(condition=self.condition,
                                  action_type=Action.DELAYED,
                                  name=action.__name__)
            action(self)

    # Recurring methods
    def get_triggered_recurring_actions(self):
        '''
        Return a list of unbound methods that are tagged with recurring_action
        and for which the interval time has passed since:
            -Either the most recent action executed for the same condition
             with the same method name
            or
            -Since the creation of the condition
        '''
        condition = self.condition
        triggered_actions = []
        for action in self._get_action_methods('recurring'):
            qry = Action.objects.filter(condition=condition,
                                        name=action.__name__,
                                        action_type=Action.RECURRING)
            if qry.count():
                last_action = qry.latest().executed
            else:
                last_action = condition.created
            if datetime.now() >= last_action + action._action_interval:
                triggered_actions.append(action)
        return triggered_actions

    def execute_recurring_actions(self):
        '''
        Execute all recurring_action methods that are triggered for execution.
        '''
        for action in self.get_triggered_recurring_actions():
            Action.objects.create(condition=self.condition,
                                  action_type=Action.RECURRING,
                                  name=action.__name__)
            action(self)

    def execute_ending_actions(self):
        '''
        Execute all methods for this object tagged with ending_action
        '''
        for action in self._get_action_methods('ending'):
            Action.objects.create(condition=self.condition,
                                  action_type=Action.ENDING,
                                  name=action.__name__)
            action(self)

    def end_condition(self, execute=True, ended_date=None):
        '''
        Set the 'ended' field of self.condition to ended_date or now(),
        (thus closing the condition) and execute all ending actions if
        execute == True
        '''
        if execute:
            self.execute_ending_actions()
        condition = self.condition
        condition.ended = ended_date or datetime.now()
        condition.save()
