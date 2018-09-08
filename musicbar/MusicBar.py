from dataclasses import dataclass
from enum import Enum
from typing import List, Any, Optional, Tuple

from applescript import AppleScript, ScriptError


class Player(Enum):
    iTunes: str = 'iTunes'
    Swinsian: str = 'Swinsian'
    Vox: str = 'Vox'
    Spotify: str = 'Spotify'


class Icons(Enum):
    def __str__(self) -> str:
        return str(self.value)

    music: str = '♫'
    paused: str = '❙ ❙'
    playing: str = '▶'
    error: str = '✗'
    pause: str = '⏸'
    next: str = '⏩'
    previous: str = '⏪'
    play: str = '▶️'


@dataclass
class Track:
    title: str
    artist: str
    album: str
    scrobbling: bool
    player: Player
    paused: bool


def run(app: str, qry: str) -> Any:
    return AppleScript(f'tell application "{app}" to {qry}').run()


class MusicBar(object):
    APPS: List[Player] = [Player.iTunes, Player.Swinsian]
    playing: List[Player] = []
    paused: List[Player] = []

    def update_playing_app(self) -> None:
        self.playing.clear()
        self.paused.clear()

        for app_idx, app in enumerate(self.APPS):
            app_state: bool = AppleScript(f'application "{app.value}" is running').run()
            if app_state:
                app_playing = run(app.value, 'player state as string')
                if app_playing in ['paused', '0']:
                    self.paused.append(app)
                elif app_playing in ['playing', '1']:
                    self.playing.append(app)

    @staticmethod
    def open(app: Player) -> None:
        run(app.value, 'activate')

    @staticmethod
    def play(app: Player) -> None:
        run(app.value, 'play')

    @staticmethod
    def pause(app: Player) -> None:
        run(app.value, 'pause')

    @staticmethod
    def next(app: Player) -> None:
        run(app.value, 'next track')
        MusicBar.play(app)

    @staticmethod
    def previous(app: Player) -> None:
        run(app.value, 'previous track')
        MusicBar.play(app)

    @staticmethod
    def get_track(app: Player, paused: bool = False) -> Optional[Track]:
        try:
            track_query = 'name of current track as string'
            artist_query = 'artist of current track as string'
            album_query = 'album of current track as string'

            scrobbling = 'application "NepTunes" is running'
            scrobbling_active = True
            if app == Player.iTunes:
                # check if neptunes is running to see if itunes will scrobble
                scrobbling_active = AppleScript(scrobbling).run()

            if app == Player.Vox:
                # Vox uses a different syntax for track and artist names
                track_query = 'track'
                artist_query = 'artist'

            track = run(app.value, track_query)
            artist = run(app.value, artist_query)
            album = run(app.value, album_query)

            return Track(title=track, artist=artist, album=album,
                         scrobbling=scrobbling_active, player=app, paused=paused)
        except ScriptError:
            return None

    def get_active_player(self) -> Tuple[Optional[Player], Optional[bool]]:
        self.update_playing_app()

        if not self.playing and not self.paused:
            return None, None

        paused = len(self.playing) == 0
        if paused:
            app = self.paused[-1]
        else:
            app = self.playing[-1]

        return app, paused

    def get_active_track(self) -> Optional[Track]:
        player, paused = self.get_active_player()
        if not player:
            return None

        return MusicBar.get_track(player, paused)

    def get_title(self, music_icon: bool = False) -> str:
        track = self.get_active_track()
        if not track:
            return str(Icons.music)

        state_icon = Icons.paused if track.paused else Icons.playing
        scrobble_warning = f' {Icons.error}' if not track.scrobbling else ''
        music = f'{Icons.music}  ' if music_icon else ''

        return f'{music}{state_icon}{scrobble_warning}  {track.title} - {track.artist}'

    @staticmethod
    def get_album_cover(player: Player) -> Optional[str]:
        # only itunes supports grabbing art right now
        if player == Player.iTunes:
            script = f'''
                tell application "{player.value}" to tell artwork 1 of current track
                    set srcBytes to raw data
                    if format is «class PNG » then
                        set ext to ".png"
                    else
                        set ext to ".jpg"
                    end if
                end tell
                set fileName to (((path to temporary items) as text) & "cover" & ext)
                set outFile to open for access file fileName with write permission
                set eof outFile to 0
                write srcBytes to outFile
                close access outFile
                do shell script "echo " & (POSIX path of fileName)
            '''
            try:
                path = AppleScript(script).run()
                if path:
                    return path
            except ScriptError:
                pass

        return None
