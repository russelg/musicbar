import threading
import time
import traceback
from typing import List, Any, Callable

import rumps
from AppKit import NSAttributedString
from Cocoa import (NSFont, NSFontAttributeName)
from Foundation import NSLog
from PyObjCTools.Conversion import propertyListFromPythonCollection
from rumps import MenuItem, quit_application

from .MusicBar import MusicBar, PlayerStatus, Icons, Track

mb = MusicBar()


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__('MusicBar', 'Your currently playing music',
                                      quit_button=None)


def _log(*_):
    pass


def debug_mode(choice):
    """Enable/disable printing helpful information for debugging the program. Default is off."""
    global _log
    rumps.debug_mode(choice)
    if choice:
        def _log(*args):
            NSLog(' '.join(map(str, args)))


debug_mode(False)


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


app = MenuBar()


def calc_string_length(title):
    font = NSFont.menuFontOfSize_(0.0)
    attributes = propertyListFromPythonCollection({NSFontAttributeName: font},
                                                  conversionHelper=lambda x: x)

    string = NSAttributedString.alloc().initWithString_attributes_(title, attributes)
    return string.size().width


def refresh(_=None) -> None:
    _log('refreshing title...')
    title, track = mb.get_title()
    size = calc_string_length(title)

    # resize the title to fit
    desired_width = 400
    if size > desired_width:
        data = mb.get_title_data()

        i = 0
        while calc_string_length(title) > desired_width:
            i += 1
            if len(data["title"]) > len(data["artist"]):
                title = f'{data["icons"]}  {data["title"][:-i]}… ー {data["artist"]}'
            else:
                title = f'{data["icons"]}  {data["title"]} ー {data["artist"][:-i]}…'

    app.title = title

    # only rebuild menu when the track changes
    if mb.previous_track != track:
        refresh_menu()

    mb.previous_track = track


@rumps.timer(20)
def refresh_menu(_=None) -> None:
    # also rebuild menu every so often
    track = mb.get_active_track()
    app.menu.clear()
    app.menu = build_menu(track)
    mb.previous_track = track


def make_font(text, font=None):
    if not font:
        font = NSFont.menuFontOfSize_(0.0)

    attributes = propertyListFromPythonCollection({NSFontAttributeName: font},
                                                  conversionHelper=lambda x: x)

    string = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    menuitem = rumps.MenuItem("")
    menuitem._menuitem.setAttributedTitle_(string)
    return menuitem


def build_menu(track: Track) -> List[Any]:
    _log('rebuilding menu...')

    def make_open(player):
        return lambda _: mb.open(player)

    players = ('Open Player', [MenuItem(f'{player.name}', callback=make_open(player))
                               for player in mb.players])

    if track:
        def cb(func) -> Callable[[Any], None]:
            def inner(_: Any) -> None:
                func(track.player.app)

                # refresh data when we do any action
                refresh()

            return inner

        buttons_paused = [MenuItem(f'{Icons.play} Play', callback=cb(mb.play))]
        buttons_playing = [MenuItem(f'{Icons.pause} Pause', callback=cb(mb.pause)),
                           MenuItem(f'{Icons.next} Next', callback=cb(mb.next)),
                           MenuItem(f'{Icons.previous} Previous', callback=cb(mb.previous))]

        buttons = buttons_paused if track.player.status == PlayerStatus.PAUSED else buttons_playing

        # art supported in itunes right now
        art_path = mb.get_album_cover(track.player.app)
        art_menu = []
        if art_path:
            art_menu = [MenuItem("", icon=art_path, dimensions=[192, 192], callback=lambda _: None),
                        None]

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

        scrobble_warning = [make_font(scrobble_message, NSFont.menuFontOfSize_(10.0)), None]

        return [
            *buttons,
            None,
            *art_menu,
            MenuItem(track.title, callback=lambda _: None),
            track.artist,
            make_font(track.album, NSFont.menuFontOfSize_(12.0)),
            None,
            f'Now playing on {track.player.app.name}',
            *scrobble_warning,
            players,
            None,
            MenuItem('Quit', callback=quit_application, key='q')
        ]
    else:
        return ['No player open currently.',
                players,
                None,
                MenuItem('Quit', callback=quit_application, key='q')]


def main():
    mb.previous_track = None
    refresh()
    # use normal threads instead because issues with rumps
    threading.Thread(target=lambda: every(2, refresh)).start()
    refresh_menu()
    app.run()
