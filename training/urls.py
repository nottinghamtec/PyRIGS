__author__ = 'Tom Price'

from django.conf.urls import patterns, url
from training import views

urlpatterns = patterns('',
    url(r'user/(?P<pk>\d+)/$', views.UserTrainingRecordView.as_view())
)
