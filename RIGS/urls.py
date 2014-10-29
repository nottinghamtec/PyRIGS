from django.conf.urls import patterns, include, url
from RIGS import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url('^user/login/$', 'RIGS.views.login', name='login'),

    # People
    url(r'^people/$', views.PersonIndex.as_view(), name='person')
)

