from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from RIGS import models

# Create your views here.
def login(request, **kwargs):
    if request.user.is_authenticated():
        next = request.REQUEST.get('next', '/')
        return HttpResponseRedirect(request.REQUEST.get('next', '/'))
    else:
        from django.contrib.auth.views import login
        return login(request)

"""
Called from a modal window (e.g. when an item is submitted to an event/invoice).
May optionally also include some javascript in a success message to cause a load of
the new information onto the page.
"""
class CloseModal(generic.TemplateView):
    template_name = 'closemodal.html'

    def get_context_data(self, **kwargs):
        from django.contrib import messages
        return {'messages', messages.get_messages(self.request)}

class PersonIndex(generic.ListView):
    model = models.Person
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', "")
        if len(q) >= 3:
            object_list = self.model.objects.filter(Q(name__icontains=q) | Q(email__icontains=q))
        else:
            object_list = self.model.objects.all()
        orderBy = self.request.GET.get('orderBy', None)
        if orderBy is not None:
            object_list = object_list.order_by(orderBy)
        return object_list

class PersonDetail(generic.DetailView):
    model = models.Person

class PersonCreate(generic.CreateView):
    model = models.Person

    def get_success_url(self):
        return reverse_lazy('person_detail', kwargs={
            'pk': self.object.pk,
        })

class PersonUpdate(generic.UpdateView):
    model = models.Person

    def get_success_url(self):
        return reverse_lazy('person_detail', kwargs={
            'pk': self.object.pk,
        })