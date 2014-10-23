from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
import RIGS

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^', include('RIGS.urls')),
    url('^user/', include('django.contrib.auth.urls')),
    url('^user/', include('registration.backends.default.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()