from contextlib import contextmanager

from django.http import HttpRequest, HttpResponse


@contextmanager
def emulate_http_request(site=None, user=None, middleware_classes=None):
    """
    Generate a fake HTTP request and run selected middleware on it.

    This is used to enable features that assume they are running as part of an HTTP request handler. Many of these
    features retrieve the "current" request from a thread local managed by crum. They will make a call like
    crum.get_current_request() or something similar.

    Since some tasks are kicked off by a management commands (which does not have an HTTP request) and then executed
    in celery workers there is no "current HTTP request". Instead we just populate the global state that is most
    commonly used on request objects.

    Arguments:
        site (Site): The site that this request should emulate. Defaults to None.
        user (User): The user that initiated this fake request. Defaults to None
        middleware_classes (list): A list of classes that implement Django's middleware interface.
    """
    request = HttpRequest()
    request.user = user
    request.site = site

    middleware_classes = middleware_classes or []
    middleware_instances = [klass() for klass in middleware_classes]
    response = HttpResponse()

    for middleware in middleware_instances:
        _run_method_if_implemented(middleware, 'process_request', request)

    try:
        yield
    except Exception as exc:
        for middleware in reversed(middleware_instances):
            _run_method_if_implemented(middleware, 'process_exception', request, exc)
    else:
        for middleware in reversed(middleware_instances):
            _run_method_if_implemented(middleware, 'process_response', request, response)


def _run_method_if_implemented(instance, method_name, *args, **kwargs):
    if hasattr(instance, method_name):
        return getattr(instance, method_name)(*args, **kwargs)
    else:
        return None
