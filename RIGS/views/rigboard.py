import copy
import datetime
import re
import premailer
import simplejson
import urllib
import hmac
import hashlib

from envparse import env
from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core import signing
from django.core.exceptions import SuspiciousOperation
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

from PyRIGS import decorators
from PyRIGS.views import OEmbedView, is_ajax, ModalURLMixin, PrintView, get_related
from RIGS import models, forms

__author__ = 'ghost'


class RigboardIndex(generic.TemplateView):
    template_name = 'rigboard.html'

    def get_context_data(self, **kwargs):
        # get super context
        context = super().get_context_data(**kwargs)

        # call out method to get current events
        context['events'] = models.Event.objects.current_events().select_related('riskassessment', 'invoice').prefetch_related('checklists')
        context['page_title'] = "Rigboard"
        return context


class WebCalendar(generic.TemplateView):
    template_name = 'calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view'] = kwargs.get('view', '')
        context['date'] = kwargs.get('date', '')
        # context['page_title'] = "Calendar"
        return context


class EventDetail(generic.DetailView, ModalURLMixin):
    template_name = 'event_detail.html'
    model = models.Event

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title = f"{self.object.display_id} | {self.object.name}"
        if self.object.dry_hire:
            title += " <span class='badge badge-secondary'>Dry Hire</span>"
        context['page_title'] = title
        if is_ajax(self.request):
            context['override'] = "base_ajax.html"
        else:
            context['override'] = 'base_assets.html'
        return context


class EventEmbed(EventDetail):
    template_name = 'event_embed.html'


class EventOEmbed(OEmbedView):
    model = models.Event
    url_name = 'event_embed'


class EventCreate(generic.CreateView):
    model = models.Event
    form_class = forms.EventForm
    template_name = 'event_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "New Event"
        context['edit'] = True
        context['currentVAT'] = models.VatRate.objects.current_rate()

        form = context['form']
        if hasattr(form, 'items_json') and re.search(r'"-\d+"', form['items_json'].value()):
            messages.info(self.request, "Your item changes have been saved. Please fix the errors and save the event.")

        get_related(form, context)

        return context

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventUpdate(generic.UpdateView):
    model = models.Event
    form_class = forms.EventForm
    template_name = 'event_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Event {self.object.display_id}"
        context['edit'] = True

        form = context['form']

        get_related(form, context)

        return context

    def render_to_response(self, context, **response_kwargs):
        if hasattr(context, 'duplicate') and not context['duplicate']:
            # If this event has already been emailed to a client, show a warning
            if self.object.auth_request_at is not None:
                messages.info(self.request,
                              'This event has already been sent to the client for authorisation, any changes you make will be visible to them immediately.')

            if hasattr(self.object, 'authorised'):
                messages.warning(self.request,
                                 'This event has already been authorised by the client, any changes to the price will require reauthorisation.')
        return super().render_to_response(context, **response_kwargs)

    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk})


class EventDuplicate(EventUpdate):
    def get_object(self, queryset=None):
        old = super().get_object(queryset)  # Get the object (the event you're duplicating)
        new = copy.copy(old)  # Make a copy of the object in memory
        new.based_on = old  # Make the new event based on the old event
        new.purchase_order = None  # Remove old PO
        new.status = new.PROVISIONAL  # Return status to provisional

        # Clear checked in by if it's a dry hire
        if new.dry_hire is True:
            new.checked_in_by = None
            new.collector = None

        # Remove all the authorisation information from the new event
        new.auth_request_to = ''
        new.auth_request_by = None
        new.auth_request_at = None

        if self.request.method in (
                'POST', 'PUT'):  # This only happens on save (otherwise items won't display in editor)
            new.pk = None  # This means a new event will be created on save, and all items will be re-created
        else:
            messages.info(self.request, 'Event data duplicated but not yet saved. Click save to complete operation.')

        return new

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Duplicate of Event {self.object.display_id}"
        context["duplicate"] = True
        return context


class EventPrint(PrintView):
    model = models.Event
    template_name = 'event_print.xml'
    append_terms = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quote'] = True
        context['filename'] = f"Event_{context['object'].display_id}_{context['object_name']}_{context['object'].start_date}.pdf"
        return context


class EventArchive(generic.ListView):
    template_name = "event_archive.html"
    model = models.Event
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['start'] = self.request.GET.get('start', None)
        context['end'] = self.request.GET.get('end', datetime.date.today().strftime('%Y-%m-%d'))
        context['statuses'] = models.Event.EVENT_STATUS_CHOICES
        context['page_title'] = 'Event Archive'
        return context

    def get_queryset(self):
        start = self.request.GET.get('start', None)
        end = self.request.GET.get('end', datetime.date.today())

        # Assume idiots, always check
        if start and start > end:
            messages.add_message(self.request, messages.INFO,
                                 "Muppet! Check the dates, it has been fixed for you.")
            start, end = end, start  # Stop the impending fail

        filter = Q()
        if end != "":
            filter &= Q(start_date__lte=end)
        if start:
            filter &= Q(start_date__gte=start)

        q = self.request.GET.get('q', "")
        objects = self.model.objects.all()

        if q:
            objects = self.model.objects.search(q)

        status = self.request.GET.getlist('status', "")

        if len(status) > 0:
            filter &= Q(status__in=status)

        qs = objects.filter(filter).order_by('-start_date')

        # Preselect related for efficiency
        qs.select_related('person', 'organisation', 'venue', 'mic')

        if not qs.exists():
            messages.add_message(self.request, messages.WARNING, "No events have been found matching those criteria.")

        return qs


class EventAuthorise(generic.UpdateView):
    template_name = 'eventauthorisation_form.html'
    success_template = 'eventauthorisation_success.html'
    preview = False

    def form_valid(self, form):
        self.object = form.save()

        self.template_name = self.success_template
        messages.add_message(self.request, messages.SUCCESS,
                             'Success! Your event has been authorised. ' +
                             f'You will also receive email confirmation to {self.object.email}.')
        return self.render_to_response(self.get_context_data())

    @property
    def event(self):
        return models.Event.objects.select_related('organisation', 'person', 'venue').get(pk=self.kwargs['pk'])

    def get_object(self, queryset=None):
        return getattr(self.event, 'authorisation', None)

    def get_form_class(self):
        return forms.InternalClientEventAuthorisationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['tos_url'] = settings.TERMS_OF_HIRE_URL
        context['page_title'] = f"{self.event.display_id}: {self.event.name}"
        if self.event.dry_hire:
            context['page_title'] += ' <span class="badge badge-secondary align-top">Dry Hire</span>'
        context['preview'] = self.preview
        return context

    def get(self, request, *args, **kwargs):
        if self.get_object() is not None and self.get_object().pk is not None:
            if self.event.authorised:
                messages.add_message(self.request, messages.WARNING,
                                     "This event has already been authorised. "
                                     "Reauthorising is not necessary at this time.")
            else:
                messages.add_message(self.request, messages.WARNING,
                                     "This event has already been authorised, but the amount has changed. " +
                                     "Please check the amount and reauthorise.")
        return super().get(request, *args, **kwargs)

    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)
        form.instance.event = self.event
        form.instance.email = self.request.email
        form.instance.sent_by = self.request.sent_by
        return form

    def dispatch(self, request, *args, **kwargs):
        # Verify our signature matches up and all is well with the integrity of the URL
        try:
            data = signing.loads(kwargs.get('hmac'))
            assert int(kwargs.get('pk')) == int(data.get('pk'))
            request.email = data['email']
            request.sent_by = models.Profile.objects.get(pk=data['sent_by'])
        except (signing.BadSignature, AssertionError, KeyError, models.Profile.DoesNotExist):
            raise SuspiciousOperation(
                "This URL is invalid. Please ask your TEC contact for a new URL")
        return super().dispatch(request, *args, **kwargs)


class EventAuthorisationRequest(generic.FormView, generic.detail.SingleObjectMixin):
    model = models.Event
    form_class = forms.EventAuthorisationRequestForm
    template_name = 'eventauthorisation_request.html'

    @method_decorator(decorators.nottinghamtec_address_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @property
    def object(self):
        return self.get_object()

    def get_success_url(self):
        if is_ajax(self.request):
            url = reverse_lazy('closemodal')
            messages.info(self.request, "location.reload()")
        else:
            url = reverse_lazy('event_detail', kwargs={
                'pk': self.object.pk,
            })
            messages.add_message(self.request, messages.SUCCESS, "Authorisation request successfully sent.")
        return url

    def form_valid(self, form):
        email = form.cleaned_data['email']
        event = self.object
        event.auth_request_by = self.request.user
        event.auth_request_at = timezone.now()
        event.auth_request_to = email
        event.save()

        context = {
            'object': self.object,
            'request': self.request,
            'hmac': signing.dumps({
                'pk': self.object.pk,
                'email': email,
                'sent_by': self.request.user.pk,
            }),
        }
        if event.person is not None and email == event.person.email:
            context['to_name'] = event.person.name
        elif event.organisation is not None and email == event.organisation.email:
            context['to_name'] = event.organisation.name

        msg = EmailMultiAlternatives(
            f"{self.object.display_id} | {self.object.name} - Event Authorisation Request",
            get_template("email/eventauthorisation_client_request.txt").render(context),
            to=[email],
            reply_to=[self.request.user.email],
        )
        css = finders.find('css/email.css')
        html = premailer.Premailer(get_template("email/eventauthorisation_client_request.html").render(context),
                                   external_styles=css).transform()
        msg.attach_alternative(html, 'text/html')

        msg.send()

        return super(EventAuthorisationRequest, self).form_valid(form)


class EventAuthoriseRequestEmailPreview(generic.DetailView):
    template_name = "email/eventauthorisation_client_request.html"
    model = models.Event

    def render_to_response(self, context, **response_kwargs):
        css = finders.find('css/email.css')
        response = super().render_to_response(context, **response_kwargs)
        assert isinstance(response, HttpResponse)
        response.content = premailer.Premailer(response.rendered_content, external_styles=css).transform()
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hmac'] = signing.dumps({
            'pk': self.object.pk,
            'email': self.request.GET.get('email', 'hello@world.test'),
            'sent_by': self.request.user.pk,
        })
        context['to_name'] = self.request.GET.get('to_name', None)
        context['target'] = 'event_authorise_form_preview'
        return context


class CreateForumThread(generic.base.RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        event = get_object_or_404(models.Event, pk=kwargs['pk'])

        if event.forum_url:
            return event.forum_url

        params = {
            'title': str(event),
            'body': f'https://rigs.nottinghamtec.co.uk/event/{event.pk}',
            'category': 'rig-info'
        }
        return f'https://forum.nottinghamtec.co.uk/new-topic?{urllib.parse.urlencode(params)}'


class RecieveForumWebhook(generic.View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        computed = f"sha256={hmac.new(env('FORUM_WEBHOOK_SECRET').encode(), request.body, hashlib.sha256).hexdigest()}"
        if not hmac.compare_digest(request.headers.get('X-Discourse-Event-Signature'), computed):
            return HttpResponseForbidden('Invalid signature header')
        # Check if this is the right kind of event. The webhook filters by category on the forum side
        if request.headers.get('X-Discourse-Event') == "topic_created":
            body = simplejson.loads(request.body.decode('utf-8'))
            event_id = int(body['topic']['title'][1:6])  # find the ID, force convert it to an int to eliminate leading zeros
            event = models.Event.objects.filter(pk=event_id).first()
            if event:
                event.forum_url = f"https://forum.nottinghamtec.co.uk/t/{body['topic']['slug']}"
                event.save()
                return HttpResponse(status=202)
        return HttpResponse(status=204)
