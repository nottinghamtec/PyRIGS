from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^user/login$', 'RIGS.views.login', name='login'),
    url('^user/', include('django.contrib.auth.urls')),
    url('^user/', include('registration.backends.default.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
