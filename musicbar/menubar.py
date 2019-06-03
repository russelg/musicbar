import os
from dataclasses import dataclass
from typing import Any, Callable, List
from threading import Lock

import rumps
from AppKit import NSAttributedString
from Cocoa import NSFont, NSFontAttributeName
from Foundation import NSLog
from PyObjCTools.Conversion import propertyListFromPythonCollection

from .enums import Icons, PlayerStatus, Track
from .utils import run
from .MusicBar import MusicBar


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
        self.first_run = True
        self.interval = 10

    def force_refresh(self, _):
        self.title = f"{Icons.music} …"
        self.previous = PreviousState()
        self.refresh()

    # @rumps.timer(10)
    def refresh_menu(self, _=None) -> None:
        self.menu.clear()
        self.menu = self.build_menu()

    @rumps.timer(1)
    def refresh(self, _=None) -> None:
        player = self.mb.get_active_player()
        if not player:
            self.title = Icons.music
            self.refresh_menu()
            return

        title, track = player.get_title()

        if title == self.previous.title:
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
        self.previous = PreviousState(
            title=title, title_width=size, track=track, status=player.status)

    def build_menu(self) -> List[Any]:
        def make_open(p):
            return lambda _: run(p.value, 'activate')

        always_visible = [
            ('Open Player',
             [rumps.MenuItem(f'{p.name}', callback=make_open(p))
              for p in self.mb.players]),
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
            scrobblers = map(lambda scrob: player.app.name if scrob is None else scrob.name,
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
