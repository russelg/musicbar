import os
from dataclasses import dataclass
from enum import Enum, EnumMeta
from typing import Any, Dict, List, Optional, Tuple

from applescript import AppleScript, ScriptError, kMissingValue

from .enums import Icons, PlayerApp, PlayerStatus, ScrobbleApp, Track
from .utils import apps_exist, apps_running, get_itunes_art, run


@dataclass
class Player:
    """A music player, including its status

    Also includes whether it is scrobbling or not"""
    app: PlayerApp
    status: PlayerStatus
    scrobbling: bool

    def get_track(self) -> Optional[Track]:
        """Return the currently playing track within the given Player.

        Returns:
            Optional[Track] -- The currently playing track for the given Player
        """
        try:
            track_query = 'name of current track'
            artist_query = 'artist of current track'
            album_query = 'album of current track'

            if self.app == PlayerApp.Vox:
                # Vox uses a different syntax for track and artist names
                track_query = 'track'
                artist_query = 'artist'
                album_query = 'album'

            script = f'''
                tell application id "{self.app.value}"
                    set trackname to {track_query}
                    set trackartist to {artist_query}
                    set trackalbum to {album_query}
                    return {{trackname, trackartist, trackalbum}}
                end tell
            '''

            def missing(val):
                if val == kMissingValue:
                    val = ''
                return val

            results = list(map(missing, AppleScript(script).run()))

            return Track(title=results[0], artist=results[1], album=results[2])
        except ScriptError as error:
            print('error: ', error)
            return None

    def get_title_data(self, music_icon: bool = False) -> Dict:
        """Return a dict of information useful for building a "now-playing" string.

        Keyword Arguments:
            music_icon {bool} -- Whether to show a persistent music icon alongside other status icons (default: {False})

        Returns:
            Dict -- Information including the current track title, artist and assorted status icons
        """
        track = self.get_track()
        if not track:
            return {
                'icons': Icons.music,
                'title': '',
                'artist': '',
                '_track': track
            }

        playback_icon = Icons.paused if self.status == PlayerStatus.PAUSED \
            else Icons.playing
        scrobble_warning = f' {Icons.error}' if not self.scrobbling else ''
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

        if data['artist'] == '':
            return f'{data["icons"]}  {data["title"]}', data['_track']

        return f'{data["icons"]}  {data["title"]} ー {data["artist"]}', data['_track']

    def open(self) -> None:
        """Open the given player."""
        run(self.app.value, 'activate')

    def play(self) -> None:
        """Resume playback of the given player."""
        run(self.app.value, 'play')

    def pause(self) -> None:
        """Pause playback of the given player."""
        run(self.app.value, 'pause')

    def next(self) -> None:
        """Play the next track within the given player."""
        run(self.app.value, 'next track')
        self.play()

    def previous(self) -> None:
        """Play the previous track within the given player."""
        run(self.app.value, 'previous track')
        self.play()

    def get_album_cover(self) -> Optional[str]:
        """Returns the path of the album art for the currently playing track.
        This is only supported by iTunes at this moment.

        Returns:
            Optional[str] -- The (temporary) path to the current album art
        """
        res = None

        # only itunes supports grabbing art right now
        if self.app == PlayerApp.iTunes:
            res = get_itunes_art(self.app.value)

        return res


class MusicBar(object):
    """Interface to obtain information from music player apps and control them"""

    def __init__(self):
        self.players: List[PlayerApp] = self.get_installed_players()
        self.scrobblers: List[ScrobbleApp] = self.get_installed_scrobblers()

    def _get_installed(self, apps: EnumMeta) -> List[Any]:
        installed = []
        appslist = list(apps)

        exists = apps_exist.run([app.value for app in appslist])
        for idx, found in enumerate(exists):
            app = appslist[idx]
            if found:
                installed.append(app)

        return installed

    def _get_running(self, apps: List[Enum]) -> List[Tuple[Any, bool]]:
        running = []
        batch_is_running = apps_running.run([app.value for app in apps])
        for idx, app in enumerate(apps):
            running.append((app, batch_is_running[idx]))

        return running

    def get_installed_players(self) -> List[PlayerApp]:
        """Return a list of currently installed music players.

        Returns:
            List[PlayerApp] -- The currently installed music players
        """
        return self._get_installed(PlayerApp)

    def get_installed_scrobblers(self) -> List[ScrobbleApp]:
        """Return a list of currently installed scrobblers.

        Returns:
            List[ScrobbleApp] -- The currently installed scrobblers
        """
        return self._get_installed(ScrobbleApp)

    def get_players(self) -> List[Player]:
        """Return a list of currently running music players.

        Arguments:
            apps {List[PlayerApp]} -- A list of music players to check

        Returns:
            List[Player] -- The currently running music players, given they are provided as input
        """
        players = []

        running = self._get_running(self.players)
        for app, app_state in running:
            if app_state:
                app_playing = run(app.value, 'player state as string')
                if app_playing in ['paused', '0']:
                    status = PlayerStatus.PAUSED
                elif app_playing in ['playing', '1']:
                    status = PlayerStatus.PLAYING
                else:
                    status = PlayerStatus.STOPPED

                scrobblers = self.get_player_scrobblers(app)
                players.append(Player(app, status, bool(scrobblers)))

        return players

    def get_scrobblers(self) -> List[ScrobbleApp]:
        """Return a list of currently running scrobblers.

        Arguments:
            apps {List[PlayerApp]} -- A list of scrobblers to check

        Returns:
            List[Player] -- The currently running scrobblers, given they are provided as input
        """
        scrobblers = []

        running = self._get_running(self.scrobblers)
        for app, app_state in running:
            if app_state:
                scrobblers.append(app)

        return scrobblers

    def get_player_scrobblers(self, player: PlayerApp) -> List[Optional[ScrobbleApp]]:
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
        if not compatible:
            # None means no scrobbler is necessary (in-built)
            return [None]

        # else return the running scrobblers
        running = self.get_scrobblers()
        return list(filter(lambda app: app in running, compatible))

    def _get_active_player(self) -> Optional[Player]:
        """Return the current foreground music player.

        Arguments:
            players {List[Player]} -- List of music players to check

        Returns:
            Optional[Player] -- The current foreground music player
        """
        active_players = self.get_players()

        paused_apps = [
            player for player in active_players if player.status == PlayerStatus.PAUSED]
        active_apps = [
            player for player in active_players if player.status == PlayerStatus.PLAYING]

        if not paused_apps and not active_apps:
            return None

        if active_apps:
            app = active_apps[-1]
        else:
            app = paused_apps[-1]

        return app

    def get_active_player(self) -> Optional[Player]:
        """Return the current foreground music player.

        Returns:
            Optional[Player] -- The current music player
        """
        return self._get_active_player()

    def get_active_track(self) -> Optional[Track]:
        """Return the currently playing track for the foreground music player.

        Returns:
            Optional[Track] -- The currently playing track
        """
        player = self.get_active_player()
        if not player:
            return None

        return player.get_track()


if __name__ == "__main__":
    # run test of app
    import cProfile

    # pr = cProfile.Profile()
    # pr.enable()
    mb = MusicBar()
    print(mb.get_installed_players())
    print(mb.get_active_player())
    # pr.disable()
    # pr.print_stats(sort='cumtime')
