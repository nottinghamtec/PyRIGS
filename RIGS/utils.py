from datetime import datetime, timedelta, date
import calendar
from calendar import HTMLCalendar
from RIGS.models import BaseEvent, Event, Subhire

def get_html(events, day):
    d = ''
    for event in events:
            # Open shared stuff
            d += f'<a href="{event.get_edit_url()}" class="modal-href"><span class="badge badge-{event.color} w-100 text-left"'
            if event.start_date.day != event.end_date.day:
                if day == event.start_date.day:
                    d += f'style="border-top-right-radius: 0; border-bottom-right-radius: 0;">{event}'
                elif day == event.end_date.day:
                    d += f'style="border-top-left-radius: 0; border-bottom-left-radius: 0;">&nbsp;'
                else:
                    d += f'style="border-radius: 0;">&nbsp;'
            else:
                d += f'{event}'
            # Close shared stuff
            d += "</span></a>"
    return d

class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    # formats a day as a td
    # filter events by day
    def formatday(self, day, events, subhires):

        d = get_html(events_per_day, day) + get_html(subhires_per_day, day)
        if day != 0:
            return f"<td valign='top' class='days'><span class='date'>{day}</span><br>{d}</td>"
        return '<td></td>'

    # formats a week as a tr
    def formatweek(self, theweek, events, subhires):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, events, subhires)
        return f'<tr> {week} </tr>'

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
                    event_html += f"<a href='{event.get_edit_url()}' style='display: contents;'><div class='event event-start event-end bg-{event.color}' data-span='{event.length}'>{event}</div></a>"
                for sh in subhires_per_day:
                    event_html += f"<div class='event event-start event-end bg-{sh.color}' data-span='{sh.length}'>{sh}</div>"
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
    month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month

def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
    return month
