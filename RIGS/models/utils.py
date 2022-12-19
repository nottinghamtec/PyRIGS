def filter_by_pk(filt, query):
    # try and parse an int
    try:
        val = int(query)
        filt = filt | Q(pk=val)
    except:  # noqa
        # not an integer
        pass
    return filt