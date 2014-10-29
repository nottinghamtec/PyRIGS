from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from RIGS import views

from PyRIGS.decorators import permission_required_with_403

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url('^user/login/$', 'RIGS.views.login', name='login'),

    # People
    url(r'^people/$', permission_required_with_403('RIGS.view_person')(views.PersonIndex.as_view()), name='person')
)

