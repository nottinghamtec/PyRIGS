from RIGS import models, forms
from django_ical.views import ICalFeed
from django.db.models import Q
from django.core.urlresolvers import reverse_lazy, reverse, NoReverseMatch
from django.utils import timezone
from django.conf import settings

import datetime, pytz

class CalendarICS(ICalFeed):
    """
    A simple event calender
    """
    #Metadata which is passed on to clients
    product_id = 'RIGS'
    title = 'RIGS Calendar'
    timezone = settings.TIME_ZONE
    file_name = "rigs.ics"

    def get(self, *args, **kwargs):
        timezone.activate(timezone.UTC)
        return super(CalendarICS, self).get(*args, **kwargs)


    def items(self):
        #include events from up to 1 year ago
        start = datetime.datetime.now() - datetime.timedelta(days=365)
        filter = Q(start_date__gte=start) & ~Q(status=models.Event.CANCELLED)

        return models.Event.objects.filter(filter).order_by('-start_date').select_related('person', 'organisation', 'venue', 'mic')

    def item_title(self, item):
        title = ''

        # Prefix title with status (if it's a critical status)
        if item.cancelled:
            title += 'CANCELLED: '

        if not item.is_rig:
            title += 'NON-RIG: '

        if item.dry_hire:
            title += 'DRY HIRE: '

        # Add the rig name
        title += item.name
        
        # Add the status
        title += ' ('+str(item.get_status_display())+')'

        return title

    def item_start_datetime(self, item):
        return item.earliest_time

    def item_end_datetime(self, item):
        return item.latest_time

    def item_location(self,item):
        return item.venue

    def item_description(self, item):
        # Create a nice information-rich description
        # note: only making use of information available to "non-keyholders"

        tz = pytz.timezone(self.timezone)

        desc = 'Rig ID = '+str(item.pk)+'\n'
        desc += 'Event = ' + item.name + '\n'
        desc += 'Venue = ' + (item.venue.name if item.venue else '---') + '\n'
        if item.is_rig and item.person:
            desc += 'Client = ' + item.person.name + ( (' for '+item.organisation.name) if item.organisation else '') + '\n'
        desc += 'Status = ' + str(item.get_status_display()) + '\n'
        desc += 'MIC = ' + (item.mic.name if item.mic else '---') + '\n'
        
        
        desc += '\n'
        if item.meet_at:
            desc += 'Crew Meet = ' + (item.meet_at.astimezone(tz).strftime('%Y-%m-%d %H:%M') if item.meet_at else '---') + '\n'
        if item.access_at:
            desc += 'Access At = ' + (item.access_at.astimezone(tz).strftime('%Y-%m-%d %H:%M') if item.access_at else '---') + '\n'
        if item.start_date:
            desc += 'Event Start = ' + item.start_date.strftime('%Y-%m-%d') + ((' '+item.start_time.strftime('%H:%M')) if item.has_start_time else '') + '\n'
        if item.end_date:
            desc += 'Event End = ' + item.end_date.strftime('%Y-%m-%d') + ((' '+item.end_time.strftime('%H:%M')) if item.has_end_time else '') + '\n'

        desc += '\n'
        if item.description:
            desc += 'Event Description:\n'+item.description+'\n\n'
        # if item.notes:  // Need to add proper keyholder checks before this gets put back
        #     desc += 'Notes:\n'+item.notes+'\n\n'  

        base_url = "http://rigs.nottinghamtec.co.uk"
        desc += 'URL = '+base_url+str(item.get_absolute_url())
        
        return desc

    def item_link(self, item):
        # Make a link to the event in the web interface
        # base_url = "https://pyrigs.nottinghamtec.co.uk"
        return item.get_absolute_url()

    # def item_created(self, item):  #TODO - Implement created date-time (using django-reversion?) - not really necessary though
    #     return ''

    def item_updated(self, item): # some ical clients will display this
        return item.last_edited_at

    def item_guid(self, item): # use the rig-id as the ical unique event identifier
        return item.pk