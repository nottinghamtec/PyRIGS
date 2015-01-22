from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from RIGS import views, rigboard

from PyRIGS.decorators import permission_required_with_403

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
                           permission_required_with_403('RIGS.change_event')(rigboard.EventDuplicate.as_view()),
                           name='event_duplicate'),

                       # API
                       url(r'^api/(?P<model>\w+)/$', (views.SecureAPIRequest.as_view()), name="api_secure"),
                       url(r'^api/(?P<model>\w+)/(?P<pk>\d+)/$', (views.SecureAPIRequest.as_view()), name="api_secure"),
)

