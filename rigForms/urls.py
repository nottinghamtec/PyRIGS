from django.conf.urls import patterns, url

from PyRIGS.decorators import permission_required_with_403

from rigForms import views

urlpatterns = patterns('',
           url(r'^create/(?P<type_pk>\d+)/for-event/(?P<event_pk>\d+)/$', permission_required_with_403('rigForms.create_form')(views.FormCreate.as_view()),
               name='create_form'),
           url(r'^(?P<pk>\d+)/$', permission_required_with_403('rigForms.update_form')(views.FormUpdate.as_view()),
               name='update_form'),
           url(r'^for-event/(?P<event_pk>\d+)/$', permission_required_with_403('rigForms.view_form')(views.FormList.as_view()),
               name='form_list'),
           url(r'^(?P<pk>\d+)/print/$', permission_required_with_403('rigForms.view_form')(views.FormPrint.as_view()), name='form_print'),
)

