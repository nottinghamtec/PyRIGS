from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from RIGS import models


def user_passes_test_with_403(test_func, login_url=None, oembed_view=None):
    """
    Decorator for views that checks that the user passes the given test.
    Anonymous users will be redirected to login_url, while users that fail
    the test will be given a 403 error.
    If embed_view is set, then a JS redirect will be used, and a application/json+oembed
    meta tag set with the url of oembed_view
    (oembed_view will be passed the kwargs from the main function)
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def _dec(view_func):
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            elif not request.user.is_authenticated():
                if oembed_view is not None:
                    extra_context = {}
                    extra_context['oembed_url'] = request.scheme + '://' + request.META['HTTP_HOST'] + reverse(oembed_view, kwargs=kwargs)
                    extra_context['login_url'] = "{0}?{1}={2}".format(login_url, REDIRECT_FIELD_NAME, request.get_full_path())
                    resp = render_to_response('login_redirect.html', extra_context, context_instance=RequestContext(request))
                    return resp
                else:
                    return HttpResponseRedirect('%s?%s=%s' % (login_url, REDIRECT_FIELD_NAME, request.get_full_path()))
            else:
                resp = render_to_response('403.html', context_instance=RequestContext(request))
                resp.status_code = 403
                return resp
        _checklogin.__doc__ = view_func.__doc__
        _checklogin.__dict__ = view_func.__dict__
        return _checklogin
    return _dec


def permission_required_with_403(perm, login_url=None, oembed_view=None):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page or rendering a 403 as necessary.
    """
    return user_passes_test_with_403(lambda u: u.has_perm(perm), login_url=login_url, oembed_view=oembed_view)


def api_key_required(function):
    """
    Decorator for views that checks api_pk and api_key.
    Failed users will be given a 403 error.
    Should only be used for urls which include <api_pk> and <api_key> kwargs
    """
    def wrap(request, *args, **kwargs):

        userid = kwargs.get('api_pk')
        key = kwargs.get('api_key')

        error_resp = render_to_response('403.html', context_instance=RequestContext(request))
        error_resp.status_code = 403

        if key is None:
            return error_resp
        if userid is None:
            return error_resp

        try:
            user_object = models.Profile.objects.get(pk=userid)
        except models.Profile.DoesNotExist:
            return error_resp

        if user_object.api_key != key:
            return error_resp
        return function(request, *args, **kwargs)
    return wrap
