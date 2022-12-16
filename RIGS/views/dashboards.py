from django.views import generic
from RIGS import models


class ProductionsDashboard(generic.TemplateView):
    template_name = 'dashboards/productions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Productions Dashboard"
        context['rig_count'] = models.Event.objects.rig_count()
        context['subhire_count'] = models.Subhire.objects.event_count()
        context['hire_count'] = models.Event.objects.active_dry_hires().count()
        return context