from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.views import generic
import models

# Create your views here.
def login(request, **kwargs):
    if request.user.is_authenticated():
        next = request.REQUEST.get('next', '/')
        return HttpResponseRedirect(request.REQUEST.get('next', '/'))
    else:
        from django.contrib.auth.views import login
        return login(request)

class PersonIndex(generic.ListView):
    model = models.Person

class PersonCreate(generic.CreateView):
    model = models.Person
    success_url = reverse_lazy('person_list')