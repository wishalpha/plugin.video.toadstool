# coding: utf-8
import sys, os, json, traceback
from urllib.parse import urlencode, quote, unquote, parse_qsl
import urllib.request
import http.cookiejar

import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon

# Plugin handle & URL
_url = sys.argv[0]
_handle = int(sys.argv[1])

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
BASE_URL = ADDON.getSetting('base_url') or 'http://127.0.0.1:3300'

COOKIE_PATH = xbmc.translatePath('special://profile/addon_data/plugin.video.lunaTV/cookies.txt')
HTTP_TIMEOUT = 20

# --------------------- Logging ---------------------
def log(msg, level=xbmc.LOGNOTICE):
    xbmc.log(f'[{ADDON_ID}] {msg}', level)

# --------------------- Cookie helpers ---------------------
def ensure_cookie_dir(path):
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def load_cookie_jar(path):
    ensure_cookie_dir(path)
    jar = http.cookiejar.LWPCookieJar()
    try:
        if os.path.exists(path):
            jar.load(path, ignore_discard=True, ignore_expires=True)
            log(f'Loaded cookies from {path}')
    except Exception as e:
        log(f'Failed loading cookies: {e}', xbmc.LOGWARNING)
    return jar

def save_cookie_jar(jar, path):
    try:
        jar.save(path, ignore_discard=True, ignore_expires=True)
        log(f'Saved cookies to {path}')
    except Exception as e:
        log(f'Failed saving cookies: {e}', xbmc.LOGERROR)

# --------------------- HTTP helpers ---------------------
def build_opener(cookiejar=None):
    if cookiejar is None:
        cookiejar = load_cookie_jar(COOKIE_PATH)
    handler = urllib.request.HTTPCookieProcessor(cookiejar)
    opener = urllib.request.build_opener(handler)
    return opener, cookiejar

def http_get(url):
    opener, jar = build_opener()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            data = resp.read()
            try:
                text = data.decode('utf-8')
            except Exception:
                text = data.decode('latin1')
            return text, resp.info()
    except Exception as e:
        log(f'HTTP GET failed: {e}', xbmc.LOGERROR)
        raise

def http_post_json(url, payload):
    opener, jar = build_opener()
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Content-Length': str(len(data)), 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            text = resp.read()
            try:
                text = text.decode('utf-8')
            except:
                text = text.decode('latin1')
        save_cookie_jar(jar, COOKIE_PATH)
        return text, resp.info()
    except Exception as e:
        log(f'HTTP POST failed: {e}', xbmc.LOGERROR)
        raise

# --------------------- Search History ---------------------
HISTORY_FILE = xbmc.translatePath("special://profile/addon_data/plugin.video.lunaTV/search_history.txt")
MAX_HISTORY = 20

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines()]
    return []

def save_history(history):
    folder = os.path.dirname(HISTORY_FILE)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(history[:MAX_HISTORY]))

def get_search_query():
    history = load_history()
    menu = ["➕ New search..."] + ["🔍 " + h for h in history]
    choice = xbmcgui.Dialog().select("Search History", menu)
    if choice < 0:
        return None
    if choice == 0:
        kb = xbmc.Keyboard('', 'Keywords')
        kb.doModal()
        if not kb.isConfirmed():
            return None
        query = kb.getText()
    else:
        query = history[choice-1]
    if query:
        if query in history:
            history.remove(query)
        history.insert(0, query)
        save_history(history)
    return query

# --------------------- Video playing ---------------------
def play_video(path):
    try:
        xbmc.log(f"LunaTV: Playing URL: {path}", xbmc.LOGINFO)
        play_item = xbmcgui.ListItem(path=path)
        play_item.setProperty('IsPlayable', 'true')
        # This tells Kodi to use InputStream Adaptive
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        
        # Specify the type of manifest (HLS or DASH)
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')  # or 'mpd' for DASH
        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    except Exception as e:
        xbmc.log(f"LunaTV: Play failed: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Play failed', str(e), xbmcgui.NOTIFICATION_ERROR)

# --------------------- Router ---------------------
def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get('action')
    if action == 'search':
        do_search()
    elif action == 'login':
        do_login()
        home_list()
    elif action == 'logout':
        clear_cookies()
        home_list()
    elif action == 'list_episodes':
        list_episodes(params.get('item_json'))
    elif action == 'play':
        play_video(params.get('url'))
    else:
        home_list()

if __name__ == '__main__':
    router(sys.argv[2][1:])
