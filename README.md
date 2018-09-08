# MusicBar
A macOS menu bar item which shows your currently playing music.

Download with `git` using:
<br />`git clone https://github.com/russelg/musicbar && cd ./musicbar`
<br />Then, install dependencies and the package with:
<br />`python3.7 setup.py install`
<br />Now you can <a href="#autorun">enable it on login using autorun.py</a>

Dependencies:
<br />`pyobjc`, `rumps` and `py-applescript`.

![Screenshot](https://user-images.githubusercontent.com/1552840/45257652-73191200-b3dc-11e8-901e-b9b968c57fd6.png)

## Player Support
Currently, the only tested players are **iTunes** and **Swinsian**.
It has the ability to also support Vox and Spotify, but these have not been tested.

I am welcoming any PRs to fix support for these players, as well as requests (submit an issue) to support any other player.

<div id="autorun"></div>

## Start on login (autorun)

Use `autorun.py` after having installed through  `setup.py` to enable the automatic start of MusicBar. Run the command `python autorun.py enable` in your terminal to enable MusicBar on login. To disable MusicBar autorun, run `python autorun.py disable`, then you can always re-enable it again.

## Notice
This is untested on anything below Python 3.7. I can guarantee this will not work without modification on anything below 3.6 due to format strings.

Do not use standard python that comes with macOS, install python ~3.7 with pip usually in `/usr/local/bin/python`, for example python from the brew package manager, e.g. `brew install python` or from the official website.

To stop `musicbar`, press the item and press 'Quit'.