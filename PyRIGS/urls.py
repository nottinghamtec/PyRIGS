from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from registration.forms import RegistrationFormUniqueEmail
from registration.backends.default.views import RegistrationView
import RIGS

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^', include('RIGS.urls')),
    url('^user/register/', RegistrationView.as_view(form_class=RegistrationFormUniqueEmail), name="registration_register"),
    url('^user/', include('django.contrib.auth.urls')),
    url('^user/', include('registration.backends.default.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()