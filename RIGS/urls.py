from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import RedirectView

from PyRIGS.decorators import (api_key_required, has_oembed,
                               permission_required_with_403)
from . import views

urlpatterns = [
    # People
    path('people/', permission_required_with_403('RIGS.view_person')(views.PersonList.as_view()),
         name='person_list'),
    path('people/add/', permission_required_with_403('RIGS.add_person')(views.PersonCreate.as_view()),
         name='person_create'),
    path('people/<int:pk>/', permission_required_with_403('RIGS.view_person')(views.PersonDetail.as_view()),
         name='person_detail'),
    path('people/<int:pk>/edit/', permission_required_with_403('RIGS.change_person')(views.PersonUpdate.as_view()),
         name='person_update'),

    # Organisations
    path('organisations/', permission_required_with_403('RIGS.view_organisation')(views.OrganisationList.as_view()),
         name='organisation_list'),
    path('organisations/add/',
         permission_required_with_403('RIGS.add_organisation')(views.OrganisationCreate.as_view()),
         name='organisation_create'),
    path('organisations/<int:pk>/',
         permission_required_with_403('RIGS.view_organisation')(views.OrganisationDetail.as_view()),
         name='organisation_detail'),
    path('organisations/<int:pk>/edit/',
         permission_required_with_403('RIGS.change_organisation')(views.OrganisationUpdate.as_view()),
         name='organisation_update'),

    # Venues
    path('venues/', permission_required_with_403('RIGS.view_venue')(views.VenueList.as_view()),
         name='venue_list'),
    path('venues/add/', permission_required_with_403('RIGS.add_venue')(views.VenueCreate.as_view()),
         name='venue_create'),
    path('venues/<int:pk>/', permission_required_with_403('RIGS.view_venue')(views.VenueDetail.as_view()),
         name='venue_detail'),
    path('venues/<int:pk>/edit/', permission_required_with_403('RIGS.change_venue')(views.VenueUpdate.as_view()),
         name='venue_update'),

    # Rigboard
    path('rigboard/', login_required(views.RigboardIndex.as_view()), name='rigboard'),
    path('rigboard/calendar/', login_required()(views.WebCalendar.as_view()),
         name='web_calendar'),
    re_path(r'^rigboard/calendar/(?P<view>(month|week|day))/$',
            login_required()(views.WebCalendar.as_view()), name='web_calendar'),
    re_path(r'^rigboard/calendar/(?P<view>(month|week|day))/(?P<date>(\d{4}-\d{2}-\d{2}))/$',
            login_required()(views.WebCalendar.as_view()), name='web_calendar'),
    path('rigboard/archive/', RedirectView.as_view(permanent=True, pattern_name='event_archive')),


    path('event/<int:pk>/', has_oembed(oembed_view="event_oembed")(views.EventDetail.as_view()),
         name='event_detail'),
    path('event/create/', permission_required_with_403('RIGS.add_event')(views.EventCreate.as_view()),
         name='event_create'),
    path('event/archive/', login_required()(views.EventArchive.as_view()),
         name='event_archive'),
    path('event/<int:pk>/embed/',
         xframe_options_exempt(login_required(login_url='/user/login/embed/')(views.EventEmbed.as_view())),
         name='event_embed'),
    path('event/<int:pk>/oembed_json/', views.EventOEmbed.as_view(),
         name='event_oembed'),
    path('event/<int:pk>/print/', permission_required_with_403('RIGS.view_event')(views.EventPrint.as_view()),
         name='event_print'),
    path('event/<int:pk>/edit/', permission_required_with_403('RIGS.change_event')(views.EventUpdate.as_view()),
         name='event_update'),
    path('event/<int:pk>/duplicate/', permission_required_with_403('RIGS.add_event')(views.EventDuplicate.as_view()),
         name='event_duplicate'),

    # Event H&S
    path('event/hs/', permission_required_with_403('RIGS.view_riskassessment')(views.HSList.as_view()), name='hs_list'),

    path('event/<int:pk>/ra/', permission_required_with_403('RIGS.add_riskassessment')(views.EventRiskAssessmentCreate.as_view()),
         name='event_ra'),
    path('event/ra/<int:pk>/', login_required(views.EventRiskAssessmentDetail.as_view()),
         name='ra_detail'),
    path('event/ra/<int:pk>/edit/', permission_required_with_403('RIGS.change_riskassessment')(views.EventRiskAssessmentEdit.as_view()),
         name='ra_edit'),
    path('event/ra/<int:pk>/review/', permission_required_with_403('RIGS.review_riskassessment')(views.MarkReviewed.as_view()),
         name='ra_review', kwargs={'model': 'RiskAssessment'}),
    path('event/ra/<int:pk>/print/', permission_required_with_403('RIGS.view_riskassessment')(views.RAPrint.as_view()), name='ra_print'),

    path('event/<int:pk>/checklist/', permission_required_with_403('RIGS.add_eventchecklist')(views.EventChecklistCreate.as_view()),
         name='event_ec'),
    path('event/checklist/<int:pk>/', login_required(views.EventChecklistDetail.as_view()),
         name='ec_detail'),
    path('event/checklist/<int:pk>/edit/', permission_required_with_403('RIGS.change_eventchecklist')(views.EventChecklistEdit.as_view()),
         name='ec_edit'),
    path('event/checklist/<int:pk>/review/', permission_required_with_403('RIGS.review_eventchecklist')(views.MarkReviewed.as_view()),
         name='ec_review', kwargs={'model': 'EventChecklist'}),

    path('event/<int:pk>/power/', permission_required_with_403('RIGS.add_powertestrecord')(views.PowerTestCreate.as_view()),
         name='event_pt'),
    path('event/power/<int:pk>/', login_required(views.PowerTestDetail.as_view()),
         name='pt_detail'),
    path('event/power/<int:pk>/edit/', permission_required_with_403('RIGS.change_powertestrecord')(views.PowerTestEdit.as_view()),
         name='pt_edit'),
    path('event/power/<int:pk>/review/', permission_required_with_403('RIGS.review_power')(views.MarkReviewed.as_view()),
         name='pt_review', kwargs={'model': 'PowerTestRecord'}),
    path('event/power/<int:pk>/print/', permission_required_with_403('RIGS.view_powertestrecord')(views.PowerPrint.as_view()), name='pt_print'),

    path('event/<int:pk>/checkin/', login_required(views.EventCheckIn.as_view()),
         name='event_checkin'),
    path('event/checkout/', login_required(views.EventCheckOut.as_view()),
         name='event_checkout'),
    path('event/<int:pk>/checkin/edit/', login_required(views.EventCheckInEdit.as_view()),
         name='edit_checkin'),
    path('event/<int:pk>/checkin/add/', login_required(views.EventCheckInOverride.as_view()),
         name='event_checkin_override'),

    path('event/<int:pk>/thread/', permission_required_with_403('RIGS.change_event')(views.CreateForumThread.as_view()), name='event_thread'),
    path('event/webhook/', views.RecieveForumWebhook.as_view(), name='webhook_recieve'),

    # Finance
    path('invoice/', permission_required_with_403('RIGS.view_invoice')(views.InvoiceDashboard.as_view()), name='invoice_dashboard'),
    path('invoice/outstanding', permission_required_with_403('RIGS.view_invoice')(views.InvoiceOutstanding.as_view()),
         name='invoice_list'),
    path('invoice/archive/', permission_required_with_403('RIGS.view_invoice')(views.InvoiceArchive.as_view()),
         name='invoice_archive'),
    path('invoice/waiting/', permission_required_with_403('RIGS.add_invoice')(views.InvoiceWaiting.as_view()),
         name='invoice_waiting'),

    path('event/<int:pk>/invoice/', permission_required_with_403('RIGS.add_invoice')(views.InvoiceEvent.as_view()),
         name='invoice_event'),
    path('event/<int:pk>/invoice/void', permission_required_with_403('RIGS.add_invoice')(views.InvoiceEvent.as_view()),
         name='invoice_event_void', kwargs={'void': True}),

    path('invoice/<int:pk>/', permission_required_with_403('RIGS.view_invoice')(views.InvoiceDetail.as_view()),
         name='invoice_detail'),
    path('invoice/<int:pk>/print/', permission_required_with_403('RIGS.view_invoice')(views.InvoicePrint.as_view()),
         name='invoice_print'),
    path('invoice/<int:pk>/void/', permission_required_with_403('RIGS.change_invoice')(views.InvoiceVoid.as_view()),
         name='invoice_void'),
    path('invoice/<int:pk>/delete/',
         permission_required_with_403('RIGS.change_invoice')(views.InvoiceDelete.as_view()),
         name='invoice_delete'),

    path('payment/create/', permission_required_with_403('RIGS.add_payment')(views.PaymentCreate.as_view()),
         name='payment_create'),
    path('payment/<int:pk>/delete/', permission_required_with_403('RIGS.add_payment')(views.PaymentDelete.as_view()),
         name='payment_delete'),

    # Client event authorisation
    path('event/<pk>/auth/',
         permission_required_with_403('RIGS.change_event')(views.EventAuthorisationRequest.as_view()),
         name='event_authorise_request'),
    path('event/<int:pk>/auth/preview/',
         permission_required_with_403('RIGS.change_event')(views.EventAuthoriseRequestEmailPreview.as_view()),
         name='event_authorise_preview'),
    re_path(r'^event/(?P<pk>\d+)/(?P<hmac>[-:\w]+)/$', views.EventAuthorise.as_view(),
            name='event_authorise'),
    re_path(r'^event/(?P<pk>\d+)/(?P<hmac>[-:\w]+)/preview/$', views.EventAuthorise.as_view(preview=True),
            name='event_authorise_form_preview'),

    # ICS Calendar - API key authentication
    re_path(r'^ical/(?P<api_pk>\d+)/(?P<api_key>\w+)/rigs.ics$', api_key_required(views.CalendarICS()),
            name="ics_calendar"),


    # Legacy URLs
    path('rig/show/<int:pk>/', RedirectView.as_view(permanent=True, pattern_name='event_detail')),
    path('bookings/', RedirectView.as_view(permanent=True, pattern_name='rigboard')),
    path('bookings/past/', RedirectView.as_view(permanent=True, pattern_name='event_archive')),
]
