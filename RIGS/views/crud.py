from PyRIGS.views import GenericListView, GenericDetailView, GenericUpdateView, GenericCreateView, ModalURLMixin
from RIGS import models


class PersonList(GenericListView):
    model = models.Person

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "People"
        context['create'] = 'person_create'
        context['edit'] = 'person_update'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_person')
        context['detail'] = 'person_detail'
        return context


class PersonDetail(GenericDetailView):
    model = models.Person

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['history_link'] = 'person_history'
        context['detail_link'] = 'person_detail'
        context['update_link'] = 'person_update'
        context['associated'] = 'partials/associated_organisations.html'
        context['associated2'] = 'partials/associated_events.html'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_person')
        return context


class PersonCreate(GenericCreateView, ModalURLMixin):
    model = models.Person
    fields = ['name', 'phone', 'email', 'address', 'notes']

    def get_success_url(self):
        return self.get_close_url('person_update', 'person_detail')


class PersonUpdate(GenericUpdateView, ModalURLMixin):
    model = models.Person
    fields = ['name', 'phone', 'email', 'address', 'notes']

    def get_success_url(self):
        return self.get_close_url('person_update', 'person_detail')


class OrganisationList(GenericListView):
    model = models.Organisation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create'] = 'organisation_create'
        context['edit'] = 'organisation_update'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_organisation')
        context['detail'] = 'organisation_detail'
        context['union_account'] = True
        return context


class OrganisationDetail(GenericDetailView):
    model = models.Organisation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['history_link'] = 'organisation_history'
        context['detail_link'] = 'organisation_detail'
        context['update_link'] = 'organisation_update'
        context['associated'] = 'partials/associated_people.html'
        context['associated2'] = 'partials/associated_events.html'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_organisation')
        return context


class OrganisationCreate(GenericCreateView, ModalURLMixin):
    model = models.Organisation
    fields = ['name', 'phone', 'email', 'address', 'notes', 'union_account']

    def get_success_url(self):
        return self.get_close_url('organisation_update', 'organisation_detail')


class OrganisationUpdate(GenericUpdateView, ModalURLMixin):
    model = models.Organisation
    fields = ['name', 'phone', 'email', 'address', 'notes', 'union_account']

    def get_success_url(self):
        return self.get_close_url('organisation_update', 'organisation_detail')


class VenueList(GenericListView):
    model = models.Venue

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create'] = 'venue_create'
        context['edit'] = 'venue_update'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_venue')
        context['detail'] = 'venue_detail'
        return context


class VenueDetail(GenericDetailView):
    model = models.Venue

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['history_link'] = 'venue_history'
        context['detail_link'] = 'venue_detail'
        context['update_link'] = 'venue_update'
        context['associated2'] = 'partials/associated_events.html'
        context['can_edit'] = self.request.user.has_perm('RIGS.change_venue')
        return context


class VenueCreate(GenericCreateView, ModalURLMixin):
    model = models.Venue
    fields = ['name', 'phone', 'email', 'address', 'notes', 'three_phase_available']

    def get_success_url(self):
        return self.get_close_url('venue_update', 'venue_detail')


class VenueUpdate(GenericUpdateView, ModalURLMixin):
    model = models.Venue
    fields = ['name', 'phone', 'email', 'address', 'notes', 'three_phase_available']

    def get_success_url(self):
        return self.get_close_url('venue_update', 'venue_detail')
