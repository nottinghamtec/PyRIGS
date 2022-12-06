from datetime import datetime, timedelta, date
import calendar
from calendar import HTMLCalendar
from RIGS.models import BaseEvent, Event, Subhire

class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    def get_html(self, day, event):
        return f"<a href='{event.get_absolute_url()}' class='modal-href' style='display: contents;'><div class='event event-start event-end bg-{event.color}' data-span='{event.length}' style='grid-column-start: calc({day[1]} + 1)'>{event}</div></a>"

    def formatmonth(self, withyear=True):
        events = Event.objects.filter(start_date__year=self.year, start_date__month=self.month)
        subhires = Subhire.objects.filter(start_date__year=self.year, start_date__month=self.month)
        weeks = self.monthdays2calendar(self.year, self.month)
        data = []

        for week in weeks:
            weeks_events = []
            for day in week:
                events_per_day = events.order_by("start_date").filter(start_date__day=day[0])
                subhires_per_day = subhires.order_by("start_date").filter(start_date__day=day[0])
                event_html = ""
                for event in events_per_day:
                    event_html += self.get_html(day, event)
                for sh in subhires_per_day:
                    event_html += self.get_html(day, sh)
                weeks_events.append((day[0], day[1], event_html))
            data.append(weeks_events)
        return data


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today()

def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = f'month={str(prev_month.year)}-{str(prev_month.month)}'
    return month

def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = f'month={str(next_month.year)}-{str(next_month.month)}'
    return month
