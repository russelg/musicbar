import os
from dataclasses import dataclass
from enum import Enum, EnumMeta, auto
from typing import Any, Dict, List, Optional, Tuple, Union

from applescript import AppleScript, ScriptError

# from .JXA import JXA


class PlayerApp(Enum):
    """A supported music player

    Maps the players name to its application bundle ID
    """
    iTunes = 'com.apple.itunes'
    Swinsian = 'com.swinsian.Swinsian'
    Vox = 'com.coppertino.Vox'
    Spotify = 'com.spotify.client'


class ScrobbleApp(Enum):
    """A supported music scrobbler

    Maps the scrobblers name to its application bundle ID
    """
    LastFM = 'fm.last.Scrobbler'
    NepTunes = 'pl.micropixels.NepTunes'
    Bowtie = 'com.13bold.Bowtie'


class PlayerStatus(Enum):
    """Current operating status of a given player"""
    NOT_OPEN = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class Player:
    """A music player, including its status

    Also includes whether it is scrobbling or not"""
    app: PlayerApp
    status: PlayerStatus
    scrobbling: bool


@dataclass
class Track:
    """A specific music track"""
    title: str
    artist: str
    album: str
    player: Player


class Icons:
    """Icons which can be used for displaying info with the menu bar"""
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

# apps_exist = JXA(
#     path=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jxa/app_exists.js'))
# apps_running = JXA(
#     path=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jxa/app_running.js'))


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
    """Tells a given application to perform a specific action

    Arguments:
        app {str or PlayerApp} -- Application ID of the app to control
        qry {str} -- The action to perform within the given app

    Returns:
        The output of the given action
    """
    script = f'tell application id "{app}" to {qry}'
    try:
        return AppleScript(script).run()
    except ScriptError as error:
        print(error)
        return None


class MusicBar(object):
    """Interface to obtain information from music player apps and control them"""

    def __init__(self):
        self.players = []
        self.scrobblers = []
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
        """Return a list of currently installed music players.

        Returns:
            List[PlayerApp] -- The currently installed music players
        """
        return MusicBar._get_installed(PlayerApp)

    @staticmethod
    def get_installed_scrobblers() -> List[ScrobbleApp]:
        """Return a list of currently installed scrobblers.

        Returns:
            List[ScrobbleApp] -- The currently installed scrobblers
        """
        return MusicBar._get_installed(ScrobbleApp)

    @staticmethod
    def get_track(player: Player) -> Optional[Track]:
        """Return the currently playing track within the given Player.

        Arguments:
            player {Player} -- The music player to query

        Returns:
            Optional[Track] -- The currently playing track for the given Player
        """
        try:
            track_query = 'name of current track'
            artist_query = 'artist of current track'
            album_query = 'album of current track'

            if player.app == PlayerApp.Vox:
                # Vox uses a different syntax for track and artist names
                track_query = 'track'
                artist_query = 'artist'
                album_query = 'album'

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
        except ScriptError as error:
            print('error: ', error)
            return None

    @staticmethod
    def get_players(apps: List[PlayerApp]) -> List[Player]:
        """Return a list of currently running music players.

        Arguments:
            apps {List[PlayerApp]} -- A list of music players to check

        Returns:
            List[Player] -- The currently running music players, given they are provided as input
        """
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
        """Return a list of currently running scrobblers.

        Arguments:
            apps {List[PlayerApp]} -- A list of scrobblers to check

        Returns:
            List[Player] -- The currently running scrobblers, given they are provided as input
        """
        scrobblers = []

        running = MusicBar._get_running(apps)
        for app, app_state in running:
            if app_state:
                scrobblers.append(app)

        return scrobblers

    @staticmethod
    def get_player_scrobblers(player: PlayerApp) -> List[Optional[ScrobbleApp]]:
        """Return a list of running scrobblers for the given Player.

        Arguments:
            player {PlayerApp} -- [description]

        Returns:
            List[Optional[ScrobbleApp]] -- [description]
        """
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
            running = MusicBar.get_scrobblers(
                MusicBar.get_installed_scrobblers())
            return [app for app in compatible if app in running]

    @staticmethod
    def get_active_player(players: List[Player]) -> Optional[Player]:
        """Return the current foreground music player.

        Arguments:
            players {List[Player]} -- List of music players to check

        Returns:
            Optional[Player] -- The current foreground music player
        """
        paused_apps = [
            player for player in players if player.status == PlayerStatus.PAUSED]
        active_apps = [
            player for player in players if player.status == PlayerStatus.PLAYING]

        if not paused_apps and not active_apps:
            return None

        if active_apps:
            app = active_apps[-1]
        else:
            app = paused_apps[-1]

        return app

    def get_active_track(self) -> Optional[Track]:
        """Return the currently playing track for the foreground music player.

        Returns:
            Optional[Track] -- The currently playing track
        """
        self._update_app_lists()
        player = MusicBar.get_active_player(self.active_players)
        if not player:
            return None

        return MusicBar.get_track(player)

    def get_title_data(self, music_icon: bool = False) -> Dict:
        """Return a dict of information useful for building a "now-playing" string.

        Keyword Arguments:
            music_icon {bool} -- Whether to show a persistent music icon alongside other status icons (default: {False})

        Returns:
            Dict -- Information including the current track title, artist and assorted status icons
        """
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
        """Return the current song information as a string, as well as the corresponding Track object.

        Keyword Arguments:
            music_icon {bool} -- Whether to show a persistent music icon alongside other status icons (default: {False})

        Returns:
            Tuple[str, Track] -- Current song information as a string, and the Track object.
        """
        data = self.get_title_data(music_icon)
        if data['title'] == '':
            return f'{data["icons"]}', data['_track']

        return f'{data["icons"]}  {data["title"]} ー {data["artist"]}', data['_track']

    @staticmethod
    def get_album_cover(player: PlayerApp) -> Optional[str]:
        """Returns the path of the album art for the currently playing track.
        This is only supported by iTunes at this moment.

        Arguments:
            player {PlayerApp} -- The player to query

        Returns:
            Optional[str] -- The (temporary) path to the current album art
        """
        res = None
        # only itunes supports grabbing art right now
        if player == PlayerApp.iTunes:
            # script = f'''
            #     tell application "{player.value}" to tell artwork 1 of current track
            #         set srcBytes to raw data
            #         if format is «class PNG » then
            #             set ext to ".png"
            #         else
            #             set ext to ".jpg"
            #         end if
            #     end tell
            #     set fileName to (((path to temporary items) as text) & "cover" & ext)
            #     set outFile to open for access file fileName with write permission
            #     set eof outFile to 0
            #     write srcBytes to outFile
            #     close access outFile
            #     do shell script "echo " & (POSIX path of fileName)
            # '''

            script_first = f'''
try
     tell application "{player.value}"
         tell artwork 1 of current track
             if format is JPEG picture then
                 set imgFormat to ".jpg"
             else
                 set imgFormat to ".png"
             end if
         end tell
         set albumName to album of current track
         set albumArtist to album artist of current track
         if length of albumArtist is 0
             set albumArtist to artist of current track
         end if
         set fileName to (do shell script "echo " & quoted form of albumArtist & quoted form of albumName & " | sed \\"s/[^a-zA-Z0-9]/_/g\\"") & imgFormat
     end tell
     do shell script "echo " & (POSIX path of (path to temporary items from user domain)) & fileName
 on error errText
     ""
 end try'''

            script_second = f'''
try
    tell application "{player.value}"
        tell artwork 1 of current track
            set srcBytes to raw data
            if format is JPEG picture then
                set imgFormat to ".jpg"
            else
                set imgFormat to ".png"
            end if
        end tell
        set albumName to album of current track
        set albumArtist to album artist of current track
        if length of albumArtist is 0
            set albumArtist to artist of current track
        end if
        set fileName to (do shell script "echo " & quoted form of albumArtist & quoted form of albumName & " | sed \\"s/[^a-zA-Z0-9]/_/g\\"") & imgFormat
    end tell
    set tmpName to ((path to temporary items from user domain) as text) & fileName
    set outFile to open for access file tmpName with write permission
    set eof outFile to 0
    write srcBytes to outFile
    close access outFile
    tell application "Image Events"
        set resImg to open tmpName
        scale resImg to size 300
        save resImg
        close resImg
    end tell
    do shell script "echo " & (POSIX path of (tmpName))
on error errText
    ""
end try'''
            try:
                res = AppleScript(script_first).run()
            except ScriptError:
                pass

            if res and not os.path.isfile(res):
                try:
                    res = AppleScript(script_second).run()
                except ScriptError:
                    pass

        return res

    @staticmethod
    def open(app: PlayerApp) -> None:
        """Open the given player."""
        run(app.value, 'activate')

    @staticmethod
    def play(app: PlayerApp) -> None:
        """Resume playback of the given player."""
        run(app.value, 'play')

    @staticmethod
    def pause(app: PlayerApp) -> None:
        """Pause playback of the given player."""
        run(app.value, 'pause')

    @staticmethod
    def next(app: PlayerApp) -> None:
        """Play the next track within the given player."""
        run(app.value, 'next track')
        MusicBar.play(app)

    @staticmethod
    def previous(app: PlayerApp) -> None:
        """Play the previous track within the given player."""
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
