"""
WSGI interface to the Mutalyzer website.

The WSGI interface is exposed through the module variable :data:`application`.
Static files are not handled by this interface and should be served through
the ``/static`` url prefix separately.

Example *Apache/mod_wsgi* configuration:

.. code-block:: apache

    Alias /static /var/www/mutalyzer/static
    WSGIScriptAlias / /usr/local/bin/mutalyzer-website

Another common practice is to use Nginx to directly serve the static files
and act as a reverse proxy server to the Mutalyzer HTTP server.

Example Nginx configuration:

.. code-block:: nginx

    server {
      listen 80;
      location /static/ {
        root /var/www/mutalyzer/static;
        if (-f $request_filename) {
          rewrite ^/static/(.*)$  /static/$1 break;
        }
      }
      location / {
        proxy_read_timeout 300;  # 5 minutes
        proxy_pass http://127.0.0.1:8080;
      }
    }

You can also use the built-in HTTP server by running this file directly. This
will give you a single-threaded server suitable for development which will
also serve the static files.
"""


from __future__ import unicode_literals

import argparse
import sys

from . import _cli_string, _ReverseProxied
from ..config import settings
from .. import website


#: WSGI application instance.
application = website.create_app()
if settings.REVERSE_PROXIED:
    application.wsgi_app = _ReverseProxied(application.wsgi_app)


def debugserver(host, port):
    """
    Run the website with the Python built-in HTTP server.
    """
    application.run(host=host, port=port, debug=True,
                    use_reloader=settings.USE_RELOADER)


def main():
    """
    Command-line interface to the website..
    """
    parser = argparse.ArgumentParser(
        description='Mutalyzer website.')
    parser.add_argument(
        '-H', '--host', metavar='HOSTNAME', type=_cli_string, dest='host',
        default='127.0.0.1', help='hostname to listen on (default: '
        '127.0.0.1; specify 0.0.0.0 to listen on all hostnames)')
    parser.add_argument(
        '-p', '--port', metavar='PORT', dest='port', type=int,
        default=8089, help='port to listen on (default: 8080)')

    args = parser.parse_args()
    debugserver(args.host, args.port)


if __name__ == '__main__':
    main()
