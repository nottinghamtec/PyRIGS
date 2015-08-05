from django.conf.urls import patterns, url

from PyRIGS.decorators import permission_required_with_403

from rigForms import views

urlpatterns = patterns('',
                       url(r'^create/(?P<type_pk>\d+)/for-event/(?P<event_pk>\d+)/$', permission_required_with_403('rigForms.create_form')(views.FormCreate.as_view()),
                           name='create_form'),
)

