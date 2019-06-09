import http.server as BaseHTTPServer
import logging
import shelve
import time
import urllib
import webbrowser
from typing import List

import pylast

from .enums import DATABASE, LASTFM_API_KEY, LASTFM_API_SECRET, Track

# data = shelve.open(DATABASE)

PORT = 5555

# The following code is taken in part from the below repo
# https://github.com/kstrauser/PythonOAuthCallback

TEMPLATE_SUCCESS = """
<html>
    <head>
        <title>Successfully authenticated</title>
        <script>
            window.close();
        </script>
    </head>
    <body>
        <p>Thanks for logging in with Last.fm! You may close this window now.</p>
    </body>
</html>
"""

TEMPLATE_FAIL = """
<html>
    <head>
        <title>Unable to authenticate</title>
    </head>
    <body>
        <p>Something bad happened!</p>
    </body>
</html>
"""

TEMPLATE_REDIRECT = """
<html>
    <head>
        <title>Redirecting</title>
        <script>
            window.location = window.location.toString().replace('#', '?');
        </script>
    </head>
</html>
"""


class LastFmAuthHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    @classmethod
    def fetch_access_token(cls, **kwargs):
        """
        Open the user's web browser to the auth URL then run a web server to
        accept and process its callback
        """
        webbrowser.open(cls.auth_url(**kwargs))

        httpd = BaseHTTPServer.HTTPServer(("", PORT), cls)
        httpd.result = None

        while httpd.result is None:
            httpd.handle_request()

        httpd.server_close()

        return httpd.result

    @staticmethod
    def auth_url(**kwargs):
        """
        Return the system-specific authentication endpoint URL
        """
        return f'http://www.last.fm/api/auth?api_key={LASTFM_API_KEY}&cb=http://127.0.0.1:5555'

    def do_GET(self):  # pylint: disable=C0103
        """
        Override this to implement system-specific callback logic
        """
        if '?' in self.path:
            querystring = urllib.parse.urlparse(self.path).query
            querydict = urllib.parse.parse_qs(querystring)
            try:
                token = querydict['token'][0]
            except KeyError:
                template = TEMPLATE_FAIL
            else:
                template = TEMPLATE_SUCCESS
                self._finish_with_result({'token': token})
        else:
            template = TEMPLATE_REDIRECT

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(template.encode('utf-8'))
        # self.wfile.close()

    def _finish_with_result(self, value):
        """
        Return the value to the server and signal it to stop answering queries
        """
        self.server.result = value


class LastFmHandler:
    def __init__(self):
        self.token: str = ''
        self.network: pylast.LastFMNetwork = None

        with shelve.open(DATABASE) as shelf:
            if 'network' in shelf:
                self.network = shelf['network']

    def _init_network(self):
        self.network = pylast.LastFMNetwork(
            api_key=LASTFM_API_KEY, api_secret=LASTFM_API_SECRET,
            token=self.token)

    def _token_mng(self, shelf):
        if 'network' not in shelf:
            self.token = LastFmAuthHandler.fetch_access_token()['token']
            self._init_network()
            shelf['network'] = self.network
        else:
            self.network = shelf['network']

    def reset(self):
        with shelve.open(DATABASE) as shelf:
            del shelf['network']
        self._init_network()

    def make_session(self):
        with shelve.open(DATABASE) as shelf:
            self._token_mng(shelf)

    @property
    def username(self):
        if self.network is not None:
            return self.network.username

        return None

    def update_now_playing(self, track: Track):
        if track and self.network:
            self.network.update_now_playing(
                artist=track.artist,
                title=track.title,
                album=track.album
            )

    def scrobble(self, track: Track):
        if track and self.network:
            start = int(time.time()) - track.position
            self.network.scrobble(
                artist=track.artist,
                title=track.title,
                album=track.album,
                timestamp=start
            )
