from django.conf.urls import patterns, url

from views import StartDiscourseAuth, ContinueDiscourseAuth, NewDiscourseUser, AssociateDiscourseUser, DisassociateDiscourseUser

urlpatterns = patterns('DiscourseAuth',
    url(r'^start/$', StartDiscourseAuth.as_view(), name='start-auth'),
    url(r'^continue/$', ContinueDiscourseAuth.as_view(), name='continue-auth'),
    url(r'^new/$', NewDiscourseUser.as_view(), name='new-user'),
    url(r'^associate/$', AssociateDiscourseUser.as_view(), name='associate-user'),
    url(r'^disassociate/$', DisassociateDiscourseUser.as_view(), name='disassociate-user')
)
