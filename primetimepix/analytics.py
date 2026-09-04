"""Server-side analytics event queue.

Conversions like signup / join / pick submit end in a redirect, so a client-side
event fired right before navigation is unreliable. Instead we stash the event in
the session; the context processor pops it on the next rendered page and the
analytics partial replays it to GA4/Plausible. Exactly-once, redirect-safe.
"""

SESSION_KEY = 'analytics_events'


def queue_event(request, name, props=None):
    """Queue an analytics event to fire on the next rendered page."""
    if not hasattr(request, 'session'):
        return
    events = request.session.get(SESSION_KEY, [])
    events.append({'name': name, 'props': props or {}})
    request.session[SESSION_KEY] = events
    request.session.modified = True


def pop_events(request):
    """Return and clear queued events (called from the context processor)."""
    if not hasattr(request, 'session'):
        return []
    events = request.session.pop(SESSION_KEY, [])
    if events:
        request.session.modified = True
    return events
