from typing import List, Any, Callable

import rumps
from AppKit import NSAttributedString
from Cocoa import (NSFont, NSFontAttributeName)
from PyObjCTools.Conversion import propertyListFromPythonCollection
from rumps import MenuItem, quit_application

from .MusicBar import MusicBar, PlayerStatus, Icons

mb = MusicBar()


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__('MusicBar', 'Your currently playing music',
                                      quit_button=None)


rumps.debug_mode(True)
app = MenuBar()


@rumps.timer(2)
def refresh(_=None) -> None:
    app.title = mb.get_title()
    app.menu.clear()
    app.menu = build_menu()


def make_font(text, font=None):
    if not font:
        font = NSFont.menuFontOfSize_(0.0)

    attributes = propertyListFromPythonCollection({NSFontAttributeName: font},
                                                  conversionHelper=lambda x: x)

    string = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
    menuitem = rumps.MenuItem("")
    menuitem._menuitem.setAttributedTitle_(string)
    return menuitem


def build_menu() -> List[Any]:
    track = mb.get_active_track()

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

        buttons_paused = [MenuItem(f'{Icons.play.value} Play', callback=cb(mb.play))]
        buttons_playing = [MenuItem(f'{Icons.pause.value} Pause', callback=cb(mb.pause)),
                           MenuItem(f'{Icons.previous.value} Next', callback=cb(mb.next)),
                           MenuItem(f'{Icons.previous.value} Previous', callback=cb(mb.previous))]

        buttons = buttons_paused if track.player.status == PlayerStatus.PAUSED else buttons_playing

        # art supported in itunes right now
        art_path = mb.get_album_cover(track.player.app)
        art_menu = []
        if art_path:
            art_menu = [MenuItem("", icon=art_path, dimensions=[192, 192], callback=lambda _: None),
                        None]

        scrobble_message = ''
        if not track.player.scrobbling:
            scrobble_message = f'{Icons.error.value} No scrobbler running'
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
    refresh()
    app.run()
