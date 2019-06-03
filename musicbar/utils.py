import os
from typing import Any

from applescript import AppleScript, ScriptError

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


def get_itunes_art(app: str):
    res = None

    script_first = f'''
try
     tell application "{app}"
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
    tell application "{app}"
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


def run(app: str, qry: str) -> Any:
    """Tells a given application to perform a specific action

    Arguments:
        app {str} -- Application ID of the app to control
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
