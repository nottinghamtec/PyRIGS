from RIGS import models, forms
from django_ical.views import ICalFeed
from django.db.models import Q

import datetime

class CalendarICS(ICalFeed):
    """
    A simple event calender
    """
    product_id = 'PyRIGS'
    title = 'PyRIGS Calendar'
    timezone = 'UTC'
    file_name = "rigs.ics"

    def items(self):
        #get events for today +- 1 year
        start = datetime.datetime.now() - datetime.timedelta(days=31*3)
        end = datetime.date.today() + datetime.timedelta(days=31*3)
        filter = Q(start_date__gte=start)

        return models.Event.objects.filter(filter).select_related('person', 'organisation', 'venue', 'mic').order_by('-start_date')

    def item_title(self, item):
        title = ''
        if item.cancelled:
            title += 'CANCELLED: '

        if not item.is_rig:
            title += 'NON-RIG: '

        if item.dry_hire:
            title += 'DRY HIRE: '

        title += item.name
        
        title += ' ('+str(item.get_status_display())+')'

        return title

    def item_start_datetime(self, item):
        #set start date to the earliest defined time for the event
        if item.meet_at:
            startDateTime = item.meet_at
        elif item.access_at:
            startDateTime = item.access_at
        elif item.start_time:
            startDateTime = datetime.datetime.combine(item.start_date,item.start_time)
        else:
            startDateTime = item.start_date

        return startDateTime

    def item_end_datetime(self, item):
        endDateTime = item.start_date

        if item.end_date:
            endDateTime = item.end_date
        
        if item.start_time and item.end_time: # don't allow an event with specific end but no specific start
            endDateTime = datetime.datetime.combine(endDateTime,item.end_time)
        elif item.start_time: # if there's a start time specified then an end time should also be specified
            endDateTime = datetime.datetime.combine(endDateTime+datetime.timedelta(days=1),datetime.time(00, 00))
        #elif item.end_time: # end time but no start time - this is weird - don't think ICS will like it so ignoring
             # do nothing

        return endDateTime

    def item_location(self,item):
        return item.venue

    def item_description(self, item):
        desc = 'Rig ID = '+str(item.pk)+'\n'
        desc += 'Event = ' + item.name + '\n'
        desc += 'Venue = ' + (item.venue.name if item.venue else '---') + '\n'
        if item.is_rig and item.person:
            desc += 'Client = ' + item.person.name + ( (' for '+item.organisation.name) if item.organisation else '') + '\n'
        desc += 'Status = ' + str(item.get_status_display()) + '\n'
        desc += 'MIC = ' + (item.mic.name if item.mic else '---') + '\n'
        
        
        desc += '\n'
        if item.meet_at:
            desc += 'Crew Meet = ' + item.meet_at.strftime('%Y-%m-%d %H:%M') + (('('+item.meet_info+')') if item.meet_info else '---') + '\n'
        if item.access_at:
            desc += 'Access At = ' + item.access_at.strftime('%Y-%m-%d %H:%M') + '\n'
        if item.start_date:
            desc += 'Event Start = ' + item.start_date.strftime('%Y-%m-%d') + ((' '+item.start_time.strftime('%H:%M')) if item.start_time else '') + '\n'
        if item.end_date:
            desc += 'Event End = ' + item.end_date.strftime('%Y-%m-%d') + ((' '+item.end_time.strftime('%H:%M')) if item.end_time else '') + '\n'

        desc += '\n'
        if item.description:
            desc += 'Event Description:\n'+item.description+'\n\n'
        if item.notes:
            desc += 'Notes:\n'+item.notes

        
        return desc

    def item_link(self, item):
        return '/event/'+str(item.pk)+'/'

    # def item_created(self, item):  #TODO - Implement created date-time (using django-reversion?)
    #     return ''

    def item_updated(self, item):
        return item.last_edited_at

    def item_guid(self, item):
        return item.pk