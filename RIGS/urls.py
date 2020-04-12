from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import RedirectView
from PyRIGS.decorators import (api_key_required, has_oembed,
                               permission_required_with_403)
from RIGS import finance, ical, models, rigboard, views
from versioning import versioning

urlpatterns = [
    path('', login_required(views.Index.as_view()), name='index'),

    path('closemodal/', views.CloseModal.as_view(), name='closemodal'),
    path('search_help/', views.SearchHelp.as_view(), name='search_help'),

    # People
    path('people/', permission_required_with_403('RIGS.view_person')(views.PersonList.as_view()),
         name='person_list'),
    path('people/add/', permission_required_with_403('RIGS.add_person')(views.PersonCreate.as_view()),
         name='person_create'),
    path('people/<int:pk>/', permission_required_with_403('RIGS.view_person')(views.PersonDetail.as_view()),
         name='person_detail'),
    path('people/<int:pk>/history/',
         permission_required_with_403('RIGS.view_person')(versioning.VersionHistory.as_view()),
         name='person_history', kwargs={'model': models.Person}),
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
    path('organisations/<int:pk>/history/',
         permission_required_with_403('RIGS.view_organisation')(versioning.VersionHistory.as_view()),
         name='organisation_history', kwargs={'model': models.Organisation}),
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
    path('venues/<int:pk>/history/',
         permission_required_with_403('RIGS.view_venue')(versioning.VersionHistory.as_view()),
         name='venue_history', kwargs={'model': models.Venue}),
    path('venues/<int:pk>/edit/', permission_required_with_403('RIGS.change_venue')(views.VenueUpdate.as_view()),
         name='venue_update'),

    # Rigboard
    path('rigboard/', login_required(rigboard.RigboardIndex.as_view()), name='rigboard'),
    path('rigboard/calendar/', login_required()(rigboard.WebCalendar.as_view()),
         name='web_calendar'),
    url(r'^rigboard/calendar/(?P<view>(month|week|day))/$',
        login_required()(rigboard.WebCalendar.as_view()), name='web_calendar'),
    url(r'^rigboard/calendar/(?P<view>(month|week|day))/(?P<date>(\d{4}-\d{2}-\d{2}))/$',
        login_required()(rigboard.WebCalendar.as_view()), name='web_calendar'),
    path('rigboard/archive/', RedirectView.as_view(permanent=True, pattern_name='event_archive')),
    path('rigboard/activity/', permission_required_with_403('RIGS.view_event')(versioning.ActivityTable.as_view()),
         name='activity_table'),
    path('rigboard/activity/feed/',
         permission_required_with_403('RIGS.view_event')(versioning.ActivityFeed.as_view()),
         name='activity_feed'),

    path('event/<int:pk>/', has_oembed(oembed_view="event_oembed")(rigboard.EventDetail.as_view()),
         name='event_detail'),
    path('event/create/', permission_required_with_403('RIGS.add_event')(rigboard.EventCreate.as_view()),
         name='event_create'),
    path('event/archive/', login_required()(rigboard.EventArchive.as_view()),
         name='event_archive'),
    path('event/<int:pk>/embed/',
         xframe_options_exempt(login_required(login_url='/user/login/embed/')(rigboard.EventEmbed.as_view())),
         name='event_embed'),
    path('event/<int:pk>/oembed_json/', rigboard.EventOembed.as_view(),
         name='event_oembed'),
    path('event/<int:pk>/print/', permission_required_with_403('RIGS.view_event')(rigboard.EventPrint.as_view()),
         name='event_print'),
    path('event/<int:pk>/ra/', permission_required_with_403('RIGS.change_event')(rigboard.EventRA.as_view()),
         name='event_ra'),
    path('event/<int:pk>/edit/', permission_required_with_403('RIGS.change_event')(rigboard.EventUpdate.as_view()),
         name='event_update'),
    path('event/<int:pk>/duplicate/', permission_required_with_403('RIGS.add_event')(rigboard.EventDuplicate.as_view()),
         name='event_duplicate'),
    path('event/<int:pk>/history/',
         permission_required_with_403('RIGS.view_event')(versioning.VersionHistory.as_view()),
         name='event_history', kwargs={'model': models.Event}),

    # Finance
    path('invoice/', permission_required_with_403('RIGS.view_invoice')(finance.InvoiceIndex.as_view()),
         name='invoice_list'),
    path('invoice/archive/', permission_required_with_403('RIGS.view_invoice')(finance.InvoiceArchive.as_view()),
         name='invoice_archive'),
    path('invoice/waiting/', permission_required_with_403('RIGS.add_invoice')(finance.InvoiceWaiting.as_view()),
         name='invoice_waiting'),

    path('event/<int:pk>/invoice/', permission_required_with_403('RIGS.add_invoice')(finance.InvoiceEvent.as_view()),
         name='invoice_event'),

    path('invoice/<int:pk>/', permission_required_with_403('RIGS.view_invoice')(finance.InvoiceDetail.as_view()),
         name='invoice_detail'),
    path('invoice/<int:pk>/print/', permission_required_with_403('RIGS.view_invoice')(finance.InvoicePrint.as_view()),
         name='invoice_print'),
    path('invoice/<int:pk>/void/', permission_required_with_403('RIGS.change_invoice')(finance.InvoiceVoid.as_view()),
         name='invoice_void'),
    path('invoice/<int:pk>/delete/',
         permission_required_with_403('RIGS.change_invoice')(finance.InvoiceDelete.as_view()),
         name='invoice_delete'),
    path('invoice/(<int:pk>/history/',
         permission_required_with_403('RIGS.view_invoice')(versioning.VersionHistory.as_view()),
         name='invoice_history', kwargs={'model': models.Invoice}),

    path('payment/create/', permission_required_with_403('RIGS.add_payment')(finance.PaymentCreate.as_view()),
         name='payment_create'),
    path('payment/<int:pk>/delete/', permission_required_with_403('RIGS.add_payment')(finance.PaymentDelete.as_view()),
         name='payment_delete'),

    # Client event authorisation
    path('event/<pk>/auth/',
         permission_required_with_403('RIGS.change_event')(rigboard.EventAuthorisationRequest.as_view()),
         name='event_authorise_request'),
    path('event/<int:pk>/auth/preview/',
         permission_required_with_403('RIGS.change_event')(rigboard.EventAuthoriseRequestEmailPreview.as_view()),
         name='event_authorise_preview'),
    url(r'^event/(?P<pk>\d+)/(?P<hmac>[-:\w]+)/$', rigboard.EventAuthorise.as_view(),
        name='event_authorise'),

    # ICS Calendar - API key authentication
    url(r'^ical/(?P<api_pk>\d+)/(?P<api_key>\w+)/rigs.ics$', api_key_required(ical.CalendarICS()),
        name="ics_calendar"),

    # Risk assessment API
    path('log_risk_assessment/', rigboard.LogRiskAssessment.as_view(), name='log_risk_assessment'),

    # Legacy URLs
    path('rig/show/<int:pk>/', RedirectView.as_view(permanent=True, pattern_name='event_detail')),
    path('bookings/', RedirectView.as_view(permanent=True, pattern_name='rigboard')),
    path('bookings/past/', RedirectView.as_view(permanent=True, pattern_name='event_archive')),
]
