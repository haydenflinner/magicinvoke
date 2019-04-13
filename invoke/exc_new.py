def reraise_with_context(orig_exc, extra_msg, new_exc_type=None):
    new_exc_type = new_exc_type or type(orig_exc)
    msg = "{}: {}\n\t{}".format(type(orig_exc).__name__, orig_exc, extra_msg)
    raise new_exc_type(msg) from orig_exc
