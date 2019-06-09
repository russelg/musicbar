from dataclasses import dataclass
from enum import Enum, auto

LASTFM_API_KEY = 'dcd6fcdca1678d1c08f773d428e7d838'
LASTFM_API_SECRET = '506ba5415b3e11f9c7bf16b0acee5598'
DATABASE = 'musicbar_options'


@dataclass
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


@dataclass
class Track:
    """A specific music track"""
    title: str
    artist: str
    album: str
    position: int
    duration: int

    def equals(self, track: 'Track'):
        if track:
            if track.artist == self.artist:
                if track.title == self.title:
                    if track.album == self.album:
                        return True

        return False

    def __str__(self):
        return f'{self.artist} - {self.title}'


class PlayerApp(Enum):
    """A supported music player

    Maps the players name to its application bundle ID
    """
    iTunes = 'com.apple.itunes'
    Music = 'com.apple.Music'
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
    MusicBar = 'co.sgfc.musicbar'


class PlayerStatus(Enum):
    """Current operating status of a given player"""
    NOT_OPEN = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()
