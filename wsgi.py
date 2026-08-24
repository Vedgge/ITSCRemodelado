"""WSGI entrypoint.

Gunicorn is invoked as `itsc:create_app()` in the container; this module exists
for platforms that expect a module-level `application` object.
"""

from itsc import create_app

application = create_app()
app = application
