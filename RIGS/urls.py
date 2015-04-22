from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from RIGS import views, rigboard, finance, ical
from django.views.generic import RedirectView

from PyRIGS.decorators import permission_required_with_403
from PyRIGS.decorators import api_key_required

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'PyRIGS.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       url('^$', views.Index.as_view(), name='index'),
                       url(r'^closemodal/$', views.CloseModal.as_view(), name='closemodal'),

                       url('^user/login/$', 'RIGS.views.login', name='login'),

                       # People
                       url(r'^people/$', permission_required_with_403('RIGS.view_person')(views.PersonList.as_view()),
                           name='person_list'),
                       url(r'^people/add/$',
                           permission_required_with_403('RIGS.add_person')(views.PersonCreate.as_view()),
                           name='person_create'),
                       url(r'^people/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_person')(views.PersonDetail.as_view()),
                           name='person_detail'),
                       url(r'^people/(?P<pk>\d+)/edit/$',
                           permission_required_with_403('RIGS.change_person')(views.PersonUpdate.as_view()),
                           name='person_update'),

                       # Organisations
                       url(r'^organisations/$',
                           permission_required_with_403('RIGS.view_organisation')(views.OrganisationList.as_view()),
                           name='organisation_list'),
                       url(r'^organisations/add/$',
                           permission_required_with_403('RIGS.add_organisation')(views.OrganisationCreate.as_view()),
                           name='organisation_create'),
                       url(r'^organisations/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_organisation')(views.OrganisationDetail.as_view()),
                           name='organisation_detail'),
                       url(r'^organisations/(?P<pk>\d+)/edit/$',
                           permission_required_with_403('RIGS.change_organisation')(views.OrganisationUpdate.as_view()),
                           name='organisation_update'),

                       # Venues
                       url(r'^venues/$',
                           permission_required_with_403('RIGS.view_venue')(views.VenueList.as_view()),
                           name='venue_list'),
                       url(r'^venues/add/$',
                           permission_required_with_403('RIGS.add_venue')(views.VenueCreate.as_view()),
                           name='venue_create'),
                       url(r'^venues/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_venue')(views.VenueDetail.as_view()),
                           name='venue_detail'),
                       url(r'^venues/(?P<pk>\d+)/edit/$',
                           permission_required_with_403('RIGS.change_venue')(views.VenueUpdate.as_view()),
                           name='venue_update'),

                       # Rigboard
                       url(r'^rigboard/$', rigboard.RigboardIndex.as_view(), name='rigboard'),
                       url(r'^rigboard/calendar/$', login_required()(rigboard.WebCalendar.as_view()), name='web_calendar'),
                       url(r'^rigboard/archive/$', RedirectView.as_view(pattern_name='event_archive')),

                       url(r'^event/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_event')(rigboard.EventDetail.as_view()),
                           name='event_detail'),
                       url(r'^event/(?P<pk>\d+)/print/$',
                           permission_required_with_403('RIGS.view_event')(rigboard.EventPrint.as_view()),
                           name='event_print'),
                       url(r'^event/create/$',
                           permission_required_with_403('RIGS.add_event')(rigboard.EventCreate.as_view()),
                           name='event_create'),
                       url(r'^event/(?P<pk>\d+)/edit/$',
                           permission_required_with_403('RIGS.change_event')(rigboard.EventUpdate.as_view()),
                           name='event_update'),
                       url(r'^event/(?P<pk>\d+)/duplicate/$',
                           permission_required_with_403('RIGS.add_event')(rigboard.EventDuplicate.as_view()),
                           name='event_duplicate'),
                       url(r'^event/archive/$', login_required()(rigboard.EventArchive.as_view()),
                           name='event_archive'),

                       url(r'^event_revisions/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_event')(rigboard.EventRevisions.as_view()),
                           name='event_revisions'),
                        url(r'^event_revision/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_event')(rigboard.EventRevision.as_view()),
                           name='event_revisions'),

                       # Finance
                       url(r'^invoice/$',
                           permission_required_with_403('RIGS.view_invoice')(finance.InvoiceIndex.as_view()),
                           name='invoice_list'),
                       url(r'^invoice/archive/$',
                           permission_required_with_403('RIGS.view_invoice')(finance.InvoiceArchive.as_view()),
                           name='invoice_archive'),
                       url(r'^invoice/waiting/$',
                           permission_required_with_403('RIGS.add_invoice')(finance.InvoiceWaiting.as_view()),
                           name='invoice_waiting'),

                       url(r'^event/(?P<pk>\d+)/invoice/$',
                           permission_required_with_403('RIGS.add_invoice')(finance.InvoiceEvent.as_view()),
                           name='invoice_event'),

                       url(r'^invoice/(?P<pk>\d+)/$',
                           permission_required_with_403('RIGS.view_invoice')(finance.InvoiceDetail.as_view()),
                           name='invoice_detail'),
                       url(r'^invoice/(?P<pk>\d+)/void/$',
                           permission_required_with_403('RIGS.change_invoice')(finance.InvoiceVoid.as_view()),
                           name='invoice_void'),
                       url(r'^payment/create/$',
                           permission_required_with_403('RIGS.add_payment')(finance.PaymentCreate.as_view()),
                           name='payment_create'),
                       url(r'^payment/(?P<pk>\d+)/delete/$',
                           permission_required_with_403('RIGS.add_payment')(finance.PaymentDelete.as_view()),
                           name='payment_delete'),

                       # User editing
                       url(r'^user/$', login_required(views.ProfileDetail.as_view()), name='profile_detail'),
                       url(r'^user/(?P<pk>\d+)/$',
                        permission_required_with_403('RIGS.view_profile')(views.ProfileDetail.as_view()), 
                        name='profile_detail'),
                       url(r'^user/edit/$', login_required(views.ProfileUpdateSelf.as_view()),
                        name='profile_update_self'),
                       url(r'^user/reset_api_key$', login_required(views.ResetApiKey.as_view(permanent=False)), name='reset_api_key'),

                       # ICS Calendar - API key authentication
                       url(r'^ical/(?P<api_pk>\d+)/(?P<api_key>\w+)/rigs.ics$', api_key_required(ical.CalendarICS()), name="ics_calendar"),

                       # API
                       url(r'^api/(?P<model>\w+)/$', (views.SecureAPIRequest.as_view()), name="api_secure"),
                       url(r'^api/(?P<model>\w+)/(?P<pk>\d+)/$', (views.SecureAPIRequest.as_view()), name="api_secure"),

                       # Legacy URL's
                       url(r'^rig/show/(?P<pk>\d+)/$', RedirectView.as_view(pattern_name='event_detail')),
                       url(r'^bookings/$', RedirectView.as_view(pattern_name='rigboard')),
                       url(r'^bookings/past/$', RedirectView.as_view(pattern_name='event_archive')),
)

