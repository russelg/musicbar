import os
from dataclasses import dataclass
from typing import Any, Callable, List

import rumps
from AppKit import NSAttributedString
from Cocoa import NSFont, NSFontAttributeName
from Foundation import NSLog
from PyObjCTools.Conversion import propertyListFromPythonCollection

from .MusicBar import Icons, MusicBar, PlayerStatus, Track


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


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__(
            'MusicBar', Icons.music, quit_button=None)

        self.mb = MusicBar()
        self.previous = PreviousState()

    @rumps.timer(10)
    def refresh_menu(self, _=None) -> None:
        track = self.mb.get_active_track()
        self.menu = self.build_menu(track)
        self.previous.track = track

    @rumps.timer(2)
    def refresh(self, _=None) -> None:
        title, track = self.mb.get_title()
        if title == self.previous.title:
            size = self.previous.title_width
        else:
            size = calc_string_length(title)

        # resize the title to fit
        desired_width = 350
        if size > desired_width:
            data = self.mb.get_title_data()
            trim = 0
            while size > desired_width:
                trim += 1
                if len(data["title"]) > len(data["artist"]):
                    title = f'{data["icons"]}  {data["title"][:-trim]}… ー {data["artist"]}'
                else:
                    title = f'{data["icons"]}  {data["title"]} ー {data["artist"][:-trim]}…'
                size = calc_string_length(title)

        self.title = title

        # only rebuild menu when the track changes
        if self.previous.track != track:
            self.refresh_menu()

        self.previous = PreviousState(
            title=title, title_width=size, track=track)

    def force_refresh(self, _):
        self.title = f"{Icons.music} …"
        self.previous = PreviousState()
        self.refresh()

    def build_menu(self, track: Track) -> List[Any]:
        # clear menu before building
        self.menu.clear()

        def make_open(player):
            return lambda _: self.mb.open(player)

        always_visible = [
            ('Open Player',
             [rumps.MenuItem(f'{player.name}', callback=make_open(player))
              for player in self.mb.players]),
            None,
            rumps.MenuItem('Force Refresh',
                           callback=self.force_refresh, key='r'),
            rumps.MenuItem('Quit', callback=rumps.quit_application, key='q')
        ]

        if not track:
            return ['No player open currently.', *always_visible]

        def make_menu_button(method):
            def cb(func) -> Callable[[Any], None]:
                def inner(_: Any) -> None:
                    func(track.player.app)
                    self.refresh()
                return inner

            attr = method.lower()
            return rumps.MenuItem(f'{getattr(Icons, attr)} {method}',
                                  callback=cb(getattr(self.mb, attr)))

        buttons_paused = [make_menu_button('Play')]
        buttons_playing = [make_menu_button('Pause'),
                           make_menu_button('Next'),
                           make_menu_button('Previous')]

        buttons = buttons_paused if track.player.status == PlayerStatus.PAUSED else buttons_playing

        # art supported in itunes right now
        art_menu = []
        art_path = self.mb.get_album_cover(track.player.app)
        if art_path and os.path.isfile(art_path):
            art_menu = [rumps.MenuItem(
                "", callback=dummy_callback, icon=art_path, dimensions=[192, 192]), None]

        if not track.player.scrobbling:
            scrobble_message = f'{Icons.error} No scrobbler running'
        else:
            scrobblers = map(lambda scrob: track.player.app.name if scrob is None else scrob.name,
                             self.mb.get_player_scrobblers(track.player.app))
            scrobble_message = f'Scrobbling using {", ".join(scrobblers)}'

        return [
            *buttons,
            None,
            *art_menu,
            rumps.MenuItem(track.title, callback=dummy_callback),
            track.artist,
            make_font(track.album, NSFont.menuFontOfSize_(12.0)),
            None,
            f'Now playing on {track.player.app.name}',
            make_font(scrobble_message, NSFont.menuFontOfSize_(10.0)),
            None,
            *always_visible
        ]


def main():
    MenuBar().run()
