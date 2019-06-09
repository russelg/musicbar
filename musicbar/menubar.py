import os
import shelve
from dataclasses import dataclass
from typing import Any, Callable, List

import rumps
from AppKit import NSAttributedString
from Cocoa import NSFont, NSFontAttributeName
from Foundation import NSLog
from PyObjCTools.Conversion import propertyListFromPythonCollection

from .enums import DATABASE, Icons, PlayerStatus, Track
from .lastfm import LastFmHandler
from .MusicBar import MusicBar
from .utils import run


def make_attributed_string(text, font=NSFont.menuFontOfSize_(0.0)):
    attributes = propertyListFromPythonCollection(
        {NSFontAttributeName: font}, conversionHelper=lambda x: x)

    return NSAttributedString.alloc().initWithString_attributes_(text, attributes)


def make_font(text, font=NSFont.menuFontOfSize_(0.0)):
    attr_string = make_attributed_string(text, font)
    menuitem = rumps.MenuItem("")
    menuitem._menuitem.setAttributedTitle_(attr_string)
    return menuitem


def calc_string_length(title):
    attr_string = make_attributed_string(title)
    return attr_string.size().width


def dummy_callback(_):
    return None


@dataclass
class PreviousState:
    title: str = None
    title_width: float = 0.0
    track: Track = None
    status: PlayerStatus = PlayerStatus.NOT_OPEN


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__(
            'MusicBar', Icons.music, quit_button=None)

        self.mb = MusicBar()
        self.previous = PreviousState()
        self.interval = 10
        self.lastfm = LastFmHandler()
        self.history: List[str] = []

        self.scrobble: bool = False
        with shelve.open(DATABASE) as shelf:
            if 'scrobble' in shelf:
                self.scrobble = shelf['scrobble']
            else:
                shelf['scrobble'] = False

    def force_refresh(self, _):
        self.title = f"{Icons.music} …"
        # self.previous = PreviousState()
        self.refresh_menu()
        self.refresh(force=True)

    def set_scrobbling(self, scrobble: bool):
        self.scrobble = scrobble
        with shelve.open(DATABASE) as shelf:
            shelf['scrobble'] = self.scrobble

    # @rumps.timer(10)
    def refresh_menu(self, _=None) -> None:
        self.menu.clear()
        self.menu = self.build_menu()

    @rumps.timer(1)
    def refresh(self, _=None, force: bool = False) -> None:
        player = self.mb.get_active_player()
        if not player:
            self.title = Icons.music
            self.refresh_menu()
            return

        title, track = player.get_title()

        if title == self.previous.title and not force:
            size = self.previous.title_width
        else:
            size = calc_string_length(title)
            self.refresh_menu()

        # resize the title to fit
        desired_width = 350
        if size > desired_width:
            data = player.get_title_data()
            trim = 0
            while size > desired_width:
                trim += 1
                if data["artist"]:
                    if len(data["title"]) > len(data["artist"]):
                        title = f'{data["icons"]}  {data["title"][:-trim]}… ー {data["artist"]}'
                    else:
                        title = f'{data["icons"]}  {data["title"]} ー {data["artist"][:-trim]}…'
                else:
                    title = f'{data["icons"]}  {data["title"][:-trim]}…'
                size = calc_string_length(title)

        self.interval -= 1
        if self.interval <= 0:
            self.refresh_menu()
            self.interval = 10

        self.title = title

        prev = self.previous.track
        if self.scrobble:
            if prev:
                # position check accounts for repeating same track
                if not prev.equals(track) or track.position < 1:
                    # new track, updating now playing
                    if track and player.status == PlayerStatus.PLAYING:
                        self.lastfm.update_now_playing(track)

                    # The track must be longer than 30 seconds.
                    # And the track has been played for at least half its duration,
                    # or for 4 minutes (whichever occurs earlier.)
                    # (from last.fm API documentation)
                    if prev.duration >= 30 and prev.position >= min(prev.duration/2, 240):
                        self.lastfm.scrobble(prev)
                        self.history.append(prev)
                        self.refresh_menu()
            else:
                if track and player.status == PlayerStatus.PLAYING:
                    self.lastfm.update_now_playing(track)

        self.previous = PreviousState(
            title=title, title_width=size, track=track, status=player.status)

    def build_lastfm_menu(self) -> List[Any]:
        def login_lastfm(_):
            self.title = f"{Icons.music} Logging into Last.fm, check your browser..."
            self.lastfm.make_session()
            self.set_scrobbling(True)
            self.refresh_menu()

        def logout_lastfm(_):
            self.lastfm.reset()
            self.refresh_menu()

        def toggle_scrobbling(_):
            self.set_scrobbling(not self.scrobble)
            self.refresh()
            self.refresh_menu()

        if not self.lastfm.username:
            self.set_scrobbling(False)
            return [
                'Not logged in.',
                None,
                rumps.MenuItem('Log in with Last.fm...', callback=login_lastfm)
            ]

        history = ['No tracks scrobbled yet...']
        if self.history:
            history = ['Last 5 Scrobbles']
            for itm in reversed(self.history[-5:]):
                history.append(
                    make_font(f'• {itm}', NSFont.menuFontOfSize_(12.0)))

        scrobble_enabled = rumps.MenuItem(
            'Enable scrobbling', callback=toggle_scrobbling)
        scrobble_enabled.state = self.scrobble

        return [
            f'Logged in as {self.lastfm.username}',
            scrobble_enabled,
            None,
            *history,
            None,
            rumps.MenuItem('Log out...', callback=logout_lastfm)
        ]

    def build_menu(self) -> List[Any]:
        def make_open(p):
            return lambda _: run(p.value, 'activate')

        always_visible = [
            ('Open Player',
             [rumps.MenuItem(f'{p.name}', callback=make_open(p))
              for p in self.mb.players]),
            None,
            ('Last.fm Scrobbling', self.build_lastfm_menu()),
            None,
            rumps.MenuItem('Force Refresh',
                           callback=self.force_refresh, key='r'),
            rumps.MenuItem('Quit', callback=rumps.quit_application, key='q')
        ]

        player = self.mb.get_active_player()
        if not player:
            return ['No player open currently.', None, *always_visible]

        track = player.get_track()
        if not track:
            return ['Nothing playing currently.', None, *always_visible]

        def make_menu_button(method):
            def cb(func) -> Callable[[Any], None]:
                def inner(_: Any) -> None:
                    func()
                    self.refresh()
                return inner

            attr = method.lower()
            return rumps.MenuItem(f'{getattr(Icons, attr)} {method}',
                                  callback=cb(getattr(player, attr)))

        buttons_paused = [make_menu_button('Play')]
        buttons_playing = [make_menu_button('Pause'),
                           make_menu_button('Next'),
                           make_menu_button('Previous')]

        buttons = buttons_paused if player.status == PlayerStatus.PAUSED else buttons_playing

        art_menu = []
        art_path = player.get_album_cover()
        if art_path and os.path.isfile(art_path):
            art_menu = [rumps.MenuItem(
                "", callback=dummy_callback, icon=art_path, dimensions=[192, 192]), None]

        if not player.scrobbling:
            scrobble_message = f'{Icons.error} No scrobbler running'
        else:
            scrobblers = map(lambda scrob: scrob.name,
                             self.mb.get_player_scrobblers(player.app))
            scrobble_message = f'Scrobbling using {", ".join(scrobblers)}'

        song_metadata = [rumps.MenuItem(track.title, callback=dummy_callback)]
        if track.artist:
            song_metadata.append(track.artist)
        if track.album:
            song_metadata.append(
                make_font(track.album, NSFont.menuFontOfSize_(12.0)))

        return [
            *buttons,
            None,
            *art_menu,
            *song_metadata,
            None,
            f'Now playing on {player.app.name}',
            make_font(scrobble_message, NSFont.menuFontOfSize_(10.0)),
            None,
            *always_visible
        ]


def main():
    MenuBar().run()
