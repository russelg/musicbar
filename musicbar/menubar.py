from typing import List, Any, Callable

import rumps
from AppKit import NSAttributedString
from Cocoa import (NSFont, NSFontAttributeName)
from PyObjCTools.Conversion import propertyListFromPythonCollection
from rumps import MenuItem, quit_application

from .MusicBar import MusicBar

mb = MusicBar()


class MenuBar(rumps.App):
    def __init__(self):
        super(MenuBar, self).__init__('MusicBar', 'Your currently playing music',
                                      quit_button=None)


rumps.debug_mode(False)
app = MenuBar()


@rumps.timer(5)
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

    players = [MenuItem(f'Open {player.value}', callback=lambda _: mb.open(player)) for player in
               mb.APPS]

    if track:
        def cb(func) -> Callable[[Any], None]:
            def inner(_: Any) -> None:
                func(track.player)

                # refresh data when we do any action
                refresh()

            return inner

        buttons_paused = [MenuItem('▶️ Play', callback=cb(mb.play))]
        buttons_playing = [MenuItem('⏸️ Pause', callback=cb(mb.pause)),
                           MenuItem('⏩ Next', callback=cb(mb.next)),
                           MenuItem('⏪ Previous', callback=cb(mb.previous))]

        buttons = buttons_paused if track.paused else buttons_playing

        # art supported in itunes right now
        art_path = mb.get_album_cover(track.player)
        art_menu = []
        if art_path:
            art_menu = [MenuItem("", icon=mb.get_album_cover(track.player), dimensions=[192, 192],
                                 callback=lambda _: None),
                        None]

        return [
            *buttons,
            None,
            *art_menu,
            MenuItem(track.title, callback=lambda _: None),
            track.artist,
            make_font(track.album, NSFont.menuFontOfSize_(12.0)),
            None,
            f'Now playing on {track.player.value}',
            *players,
            None,
            MenuItem('Quit', callback=quit_application, key='q')
        ]
    else:
        return ['No player open currently.',
                *players,
                None,
                MenuItem('Quit', callback=quit_application, key='q')]


def main():
    refresh()
    app.run()
