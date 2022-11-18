from datetime import datetime, timedelta, date
import calendar
from calendar import HTMLCalendar
from RIGS.models import BaseEvent, Event, Subhire

class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    # formats a day as a td
    # filter events by day
    def formatday(self, day, events, subhires):
        events_per_day = events.filter(start_date__day=day)
        subhires_per_day = subhires.filter(start_date__day=day)
        d = ''
        for event in events_per_day:
            d += f'{event.get_html_url}<br>'
        for subhire in subhires_per_day:
            d += f'{subhire.get_html_url}<br>'

        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return '<td></td>'

    # formats a week as a tr
    def formatweek(self, theweek, events, subhires):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, events, subhires)
        return f'<tr> {week} </tr>'

    # formats a month as a table
    # filter events by year and month
    def formatmonth(self, withyear=True):
        events = Event.objects.filter(start_date__year=self.year, start_date__month=self.month)
        subhires = Subhire.objects.filter(start_date__year=self.year, start_date__month=self.month)

        cal = f'<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, events, subhires)}\n'
        return cal


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
