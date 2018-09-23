from dataclasses import dataclass
from enum import Enum, auto, EnumMeta
from typing import List, Any, Optional, Union, Dict, Tuple

from applescript import AppleScript, ScriptError


class PlayerApp(Enum):
    iTunes = 'com.apple.itunes'
    Swinsian = 'com.swinsian.Swinsian'
    Vox = 'com.coppertino.Vox'
    Spotify = 'com.spotify.client'


class ScrobbleApp(Enum):
    LastFM = 'fm.last.Scrobbler'
    NepTunes = 'pl.micropixels.NepTunes'
    Bowtie = 'com.13bold.Bowtie'


class PlayerStatus(Enum):
    NOT_OPEN = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class Player:
    app: PlayerApp
    status: PlayerStatus
    scrobbling: bool


@dataclass
class Track:
    title: str
    artist: str
    album: str
    player: Player


class Icons:
    music = '♫'
    paused = '❙ ❙'
    playing = '▶'
    error = '✗'
    pause = '⏸'
    next = '⏩'
    previous = '⏪'
    play = '▶️'


apps_exist = AppleScript('''
    on run {appList}
        repeat with a from 1 to length of appList
            set appname to item a of appList
            try
                tell application "Finder" to get application file id appname
                set item a of appList to true
            on error
                set item a of appList to false
            end try
        end repeat
        
        return appList
    end run
''')

apps_running = AppleScript('''
    on run {appList}
        repeat with a from 1 to length of appList
            set appname to item a of appList
            set item a of appList to (application id appname is running)
        end repeat
        
        return appList
    end run
''')


def run(app: Union[str, PlayerApp], qry: str) -> Any:
    script = f'tell application id "{app}" to {qry}'
    try:
        return AppleScript(script).run()
    except ScriptError as e:
        print(e)
        return None


class MusicBar(object):
    def __init__(self):
        self._update_app_lists(installed=True)

    def _update_app_lists(self, installed=False):
        if installed or not (self.players or self.scrobblers):
            self.players = self.get_installed_players()
            self.scrobblers = self.get_installed_scrobblers()

        self.active_players = self.get_players(self.players)
        self.active_scrobblers = self.get_scrobblers(self.scrobblers)

    @staticmethod
    def _get_installed(apps: EnumMeta) -> List[Any]:
        installed = []
        appslist = list(apps)

        exists = apps_exist.run([app.value for app in appslist])
        for idx, found in enumerate(exists):
            app = appslist[idx]
            if found:
                installed.append(app)

        return installed

    @staticmethod
    def _get_running(apps: List[Enum]) -> List[Tuple[Any, bool]]:
        running = []
        batch_is_running = apps_running.run([app.value for app in apps])
        for idx, app in enumerate(apps):
            running.append((app, batch_is_running[idx]))

        return running

    @staticmethod
    def get_installed_players() -> List[PlayerApp]:
        return MusicBar._get_installed(PlayerApp)

    @staticmethod
    def get_installed_scrobblers() -> List[ScrobbleApp]:
        return MusicBar._get_installed(ScrobbleApp)

    @staticmethod
    def get_track(player: Player) -> Optional[Track]:
        try:
            track_query = 'name of current track'
            artist_query = 'artist of current track'
            album_query = 'album of current track'

            if player.app == PlayerApp.Vox:
                # Vox uses a different syntax for track and artist names
                track_query = 'track'
                artist_query = 'artist'
                album_query = 'album'

            # language=applescript
            script = f'''
                tell application id "{player.app.value}"
                    set trackname to {track_query}
                    set trackartist to {artist_query}
                    set trackalbum to {album_query}
                    return {{trackname, trackartist, trackalbum}}
                end tell
            '''

            results = AppleScript(script).run()
            return Track(title=results[0], artist=results[1], album=results[2],
                         player=player)
        except ScriptError as e:
            print('error: ', e)
            return None

    @staticmethod
    def get_players(apps: List[PlayerApp]) -> List[Player]:
        players = []

        running = MusicBar._get_running(apps)
        for app, app_state in running:
            if app_state:
                app_playing = run(app.value, 'player state as string')
                if app_playing in ['paused', '0']:
                    status = PlayerStatus.PAUSED
                elif app_playing in ['playing', '1']:
                    status = PlayerStatus.PLAYING
                else:
                    status = PlayerStatus.STOPPED

                scrobblers = MusicBar.get_player_scrobblers(app)
                players.append(Player(app, status, bool(scrobblers)))

        return players

    @staticmethod
    def get_scrobblers(apps: List[ScrobbleApp]) -> List[ScrobbleApp]:
        scrobblers = []

        running = MusicBar._get_running(apps)
        for app, app_state in running:
            if app_state:
                scrobblers.append(app)

        return scrobblers

    @staticmethod
    def get_player_scrobblers(player: PlayerApp) -> List[Optional[ScrobbleApp]]:
        possible = {
            PlayerApp.iTunes: [ScrobbleApp.NepTunes, ScrobbleApp.LastFM, ScrobbleApp.Bowtie],
            PlayerApp.Spotify: [ScrobbleApp.NepTunes, ScrobbleApp.LastFM, ScrobbleApp.Bowtie],
            PlayerApp.Vox: [ScrobbleApp.LastFM],
            PlayerApp.Swinsian: []
        }

        compatible = possible.get(player, [])
        if len(compatible) == 0:
            # None means no scrobbler is necessary (in-built)
            return [None]
        else:
            # else return the running scrobblers
            running = MusicBar.get_scrobblers(MusicBar.get_installed_scrobblers())
            return [app for app in compatible if app in running]

    @staticmethod
    def get_active_player(players: List[Player]) -> Optional[Player]:
        paused_apps = [player for player in players if player.status == PlayerStatus.PAUSED]
        active_apps = [player for player in players if player.status == PlayerStatus.PLAYING]

        if not paused_apps and not active_apps:
            return None

        if active_apps:
            app = active_apps[-1]
        else:
            app = paused_apps[-1]

        return app

    def get_active_track(self) -> Optional[Track]:
        self._update_app_lists()
        player = MusicBar.get_active_player(self.active_players)
        if not player:
            return None

        return MusicBar.get_track(player)

    def get_title_data(self, music_icon: bool = False) -> Dict:
        track = self.get_active_track()
        if not track:
            return {
                'icons': Icons.music,
                'title': '',
                'artist': '',
                '_track': track
            }

        playback_icon = Icons.paused if track.player.status == PlayerStatus.PAUSED \
            else Icons.playing
        scrobble_warning = f' {Icons.error}' if not track.player.scrobbling else ''
        music = f'{Icons.music}  ' if music_icon else ''

        return {
            'icons': f'{music}{playback_icon}{scrobble_warning}',
            'title': track.title,
            'artist': track.artist,
            '_track': track
        }

    def get_title(self, music_icon: bool = False) -> Tuple[str, Track]:
        data = self.get_title_data(music_icon)
        if data['title'] == '':
            return f'{data["icons"]}', data['_track']

        return f'{data["icons"]}  {data["title"]} ー {data["artist"]}', data['_track']

    @staticmethod
    def get_album_cover(player: PlayerApp) -> Optional[str]:
        # only itunes supports grabbing art right now
        if player == PlayerApp.iTunes:
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
                return AppleScript(script).run()
            except ScriptError:
                pass

        return None

    @staticmethod
    def open(app: PlayerApp) -> None:
        run(app.value, 'activate')

    @staticmethod
    def play(app: PlayerApp) -> None:
        run(app.value, 'play')

    @staticmethod
    def pause(app: PlayerApp) -> None:
        run(app.value, 'pause')

    @staticmethod
    def next(app: PlayerApp) -> None:
        run(app.value, 'next track')
        MusicBar.play(app)

    @staticmethod
    def previous(app: PlayerApp) -> None:
        run(app.value, 'previous track')
        MusicBar.play(app)


if __name__ == "__main__":
    # run test of app
    import cProfile

    pr = cProfile.Profile()
    pr.enable()
    mb = MusicBar()
    print(mb.get_title())
    pr.disable()
    pr.print_stats(sort='cumtime')
