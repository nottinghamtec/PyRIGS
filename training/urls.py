__author__ = 'Tom Price'

from django.conf.urls import patterns, url
from training import views

urlpatterns = patterns('',
    url(r'^$', views.SelfUserTrainingRecordView.as_view()),
    url(r'user/(?P<pk>\d+)/$', views.UserTrainingRecordView.as_view())
)
