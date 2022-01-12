from PyRIGS.decorators import user_passes_test_with_403


def has_perm_or_supervisor(perm, login_url=None, oembed_view=None):
    return user_passes_test_with_403(lambda u: (hasattr(u, 'is_supervisor') and u.is_supervisor) or u.has_perm(perm), login_url=login_url, oembed_view=oembed_view)
