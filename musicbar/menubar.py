import os
import time
import traceback
from typing import Any, Callable, List

import rumps
from AppKit import NSAttributedString
from Cocoa import NSFont, NSFontAttributeName
from Foundation import NSLog
from PyObjCTools.Conversion import propertyListFromPythonCollection

from .MusicBar import Icons, MusicBar, PlayerStatus, Track

mb = MusicBar()


def every(delay, task):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        try:
            task()
        except Exception:
            traceback.print_exc()
        # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay


def calc_string_length(title):
    font = NSFont.menuFontOfSize_(0.0)
    attributes = propertyListFromPythonCollection({NSFontAttributeName: font},
                                                  conversionHelper=lambda x: x)

    string = NSAttributedString.alloc().initWithString_attributes_(title, attributes)
    return string.size().width


def make_font(text, font=None):
    if not font:
        font = NSFont.menuFontOfSize_(0.0)

    attributes = propertyListFromPythonCollection({NSFontAttributeName: font},
                                                  conversionHelper=lambda x: x)

    string = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    menuitem = rumps.MenuItem("")
    menuitem._menuitem.setAttributedTitle_(string)
    return menuitem


def dummy_callback(_):
    return None


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__(
            'MusicBar', Icons.music, quit_button=None)

        self.previous_title = {
            'title': None,
            'size': 0.0
        }
        self.previous_track = None
        # self.refresh()
        # self.refresh_menu()
        # self.force_refresh()

    @rumps.timer(10)
    def refresh_menu(self, _=None) -> None:
        track = mb.get_active_track()
        self.menu.clear()
        self.menu = self.build_menu(track)
        self.previous_track = track

    @rumps.timer(1)
    def refresh(self, _=None) -> None:
        title, track = mb.get_title()
        if title == self.previous_title['title']:
            size = self.previous_title['size']
        else:
            size = calc_string_length(title)

        # resize the title to fit
        desired_width = 350
        if size > desired_width:
            data = mb.get_title_data()

            i = 0
            while calc_string_length(title) > desired_width:
                i += 1
                if len(data["title"]) > len(data["artist"]):
                    title = f'{data["icons"]}  {data["title"][:-i]}… ー {data["artist"]}'
                else:
                    title = f'{data["icons"]}  {data["title"]} ー {data["artist"][:-i]}…'

        self.title = title
        self.previous_title = {
            'title': title, 'size': size
        }

        # only rebuild menu when the track changes
        if self.previous_track != track:
            self.refresh_menu()

        self.previous_track = track

    def force_refresh(self, _):
        self.title = "…"
        self.previous_title = {'title': None, 'size': 0.0}
        self.refresh()
        self.refresh_menu()

    def build_menu(self, track: Track) -> List[Any]:
        def make_open(player):
            return lambda _: mb.open(player)

        players = ('Open Player',
                   [rumps.MenuItem(f'{player.name}',
                                   callback=make_open(player))
                    for player in mb.players])

        refresh_entry = rumps.MenuItem(
            'Force Refresh', callback=self.force_refresh, key='r')

        if track:
            def cb(func) -> Callable[[Any], None]:
                def inner(_: Any) -> None:
                    func(track.player.app)
                    self.refresh()
                return inner

            buttons_paused = [
                rumps.MenuItem(f'{Icons.play} Play', callback=cb(mb.play))]
            buttons_playing = [rumps.MenuItem(f'{Icons.pause} Pause', callback=cb(mb.pause)),
                               rumps.MenuItem(f'{Icons.next} Next',
                                              callback=cb(mb.next)),
                               rumps.MenuItem(f'{Icons.previous} Previous', callback=cb(mb.previous))]

            buttons = buttons_paused if track.player.status == PlayerStatus.PAUSED else buttons_playing

            # art supported in itunes right now
            art_menu = []
            art_path = mb.get_album_cover(track.player.app)
            if art_path and os.path.isfile(art_path):
                art_menu = [rumps.MenuItem(
                    "", callback=dummy_callback, icon=art_path, dimensions=[192, 192]), None]

            if not track.player.scrobbling:
                scrobble_message = f'{Icons.error} No scrobbler running'
            else:
                scrobblers = []
                for scrobbler in mb.get_player_scrobblers(track.player.app):
                    if scrobbler is None:
                        scrobblers.append(track.player.app.name)
                    else:
                        scrobblers.append(scrobbler.name)

                scrobble_message = f'Scrobbling using {", ".join(scrobblers)}'

            scrobbler_info = [
                make_font(scrobble_message, NSFont.menuFontOfSize_(10.0)), None]

            return [
                *buttons,
                None,
                *art_menu,
                rumps.MenuItem(track.title, callback=dummy_callback),
                track.artist,
                make_font(track.album, NSFont.menuFontOfSize_(12.0)),
                None,
                f'Now playing on {track.player.app.name}',
                *scrobbler_info,
                players,
                None,
                refresh_entry,
                rumps.MenuItem(
                    'Quit', callback=rumps.quit_application, key='q')
            ]
        else:
            return ['No player open currently.',
                    players,
                    None,
                    refresh_entry,
                    rumps.MenuItem('Quit', callback=rumps.quit_application, key='q')]


# rumps.debug_mode(False)

def main():
    MenuBar().run()
