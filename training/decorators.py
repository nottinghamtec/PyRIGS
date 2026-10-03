from PyRIGS.decorators import user_passes_test_with_403


def is_supervisor(login_url=None, oembed_view=None):
    return user_passes_test_with_403(lambda u: hasattr(u, "is_supervisor") and u.is_supervisor)


def is_supervisor_or_technician(login_url=None, oembed_view=None):
    return user_passes_test_with_403(lambda u: u.is_authenticated and u.can_log_training)
