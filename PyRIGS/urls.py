from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from registration.backends.default.views import RegistrationView
import RIGS
from RIGS import regbackend

urlpatterns = [
    # Examples:
    # url(r'^$', 'PyRIGS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^', include('RIGS.urls')),
    url('^user/register/$', RegistrationView.as_view(form_class=RIGS.forms.ProfileRegistrationFormUniqueEmail),
        name="registration_register"),
    url('^user/', include('django.contrib.auth.urls')),
    url('^user/', include('registration.backends.default.urls')),

    url(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
