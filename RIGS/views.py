from django.shortcuts import render
from django.http.response import HttpResponseRedirect

# Create your views here.
def login(request, **kwargs):
    if request.user.is_authenticated():
        next = request.REQUEST.get('next', '/')
        return HttpResponseRedirect(request.REQUEST.get('next', '/'))
    else:
        from django.contrib.auth.views import login
        return login(request)