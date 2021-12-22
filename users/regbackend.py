from registration.signals import user_registered

from users.forms import ProfileRegistrationFormUniqueEmail


def user_created(sender, user, request, **kwargs):
    form = ProfileRegistrationFormUniqueEmail(request.POST)
    user.first_name = form.data['first_name']
    user.last_name = form.data['last_name']
    user.initials = form.data['initials']
    # user.phone = form.data['phone']
    user.save()


user_registered.connect(user_created)
