# MusicBar
A macOS menu bar item which shows your currently playing music.

![Screenshot](https://sgfc.co/YbBH.png)

Compiled app bundles are available under the Releases tab.

## Player Support
Currently, the only tested players are **iTunes** and **Swinsian**.
It has the ability to also support Vox and Spotify, but these have not been well-tested as I do not use them.

I am welcoming any PRs to fix support for these players (if needed), as well as requests (submit an issue) to support any other player.

<br />

# Developers

This is untested on anything below Python 3.7. I can guarantee this will not work without modification on anything below 3.6 due to format strings.

Do not use standard python that comes with macOS, install python ~3.7 with pip usually in `/usr/local/bin/python`, for example python from the brew package manager, e.g. `brew install python` or from the official website.

## Dependencies

`pyobjc`, `rumps` and `py-applescript`.

Install dependencies using pipenv:
<br />`pipenv install`


## Building, developing and distributing

A macOS .app executable (for distribution) can be made using:
<br />`pipenv run python setup.py py2app`

A macOS .app executable (for development) can be made using:
<br />`pipenv run python setup.py py2app -A`

Do not distribute the development .app bundle as this is non-portable.