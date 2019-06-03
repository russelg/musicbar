from dataclasses import dataclass
from enum import Enum, auto


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
