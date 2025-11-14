# -*- coding: utf-8 -*-
# default.py for Kodi 18 (Python 2)


import sys
import os
import json
import urllib
import urllib2
import urlparse
import cookielib
import traceback


import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon


# --------------------- configuration ---------------------
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE = int(sys.argv[1])
BASE_URL = ADDON.getSetting('base_url') or 'http://120.0.0.1:3300'
API_SEARCH = '/api/search'
API_LOGIN = '/api/login'


# Cookie file path (Netscape format)
COOKIE_PATH = ADDON.getSetting('cookie_path') or xbmc.translatePath('special://sotrage/cookies.txt')
HTTP_TIMEOUT = 20


# --------------------- logging ---------------------
def log(msg, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


# --------------------- cookie helpers ---------------------


def ensure_cookie_dir(path):
    d = os.path.dirname(path)
    if not os.path.exists(d):
        try:
            os.makedirs(d)
        except Exception:
            pass




def load_cookie_jar(path):
    ensure_cookie_dir(path)
    jar = cookielib.MozillaCookieJar(path)
    try:
        if os.path.exists(path):
            jar.load(ignore_discard=True, ignore_expires=True)
            log('Loaded cookies from %s' % path)
    except Exception as e:
        log('Failed loading cookies: %s' % str(e), xbmc.LOGWARNING)
    return jar




def save_cookie_jar(jar, path):
    try:
        jar.save(path, ignore_discard=True, ignore_expires=True)
        log('Saved cookies to %s' % path)
    except Exception as e:
        log('Failed saving cookies: %s' % str(e), xbmc.LOGERROR)


# --------------------- HTTP helpers ---------------------


def build_opener(cookiejar=None):
    if cookiejar is None:
        cookiejar = load_cookie_jar(COOKIE_PATH)
        handler = urllib2.HTTPCookieProcessor(cookiejar)
        opener = urllib2.build_opener(handler)
        opener.addheaders = [('User-agent', 'Kodi-dytt-search/1.0')]
    return opener, cookiejar




def http_get(url):
    opener, jar = build_opener()
    try:
        resp = opener.open(url, timeout=HTTP_TIMEOUT)
        data = resp.read()
        # try decode utf-8, fallback to latin-1
        try:
            text = data.decode('utf-8')
        except Exception:
            text = data.decode('latin1')
        return text, resp.info()
    except Exception as e:
        log('HTTP GET failed: %s' % str(e), xbmc.LOGERROR)
        raise

def http_post_json(url, payload):
    opener, jar = build_opener()
    data = json.dumps(payload)
    req = urllib2.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        resp = opener.open(req, timeout=HTTP_TIMEOUT)
        text = resp.read()
        try:
            text = text.decode('utf-8')
        except Exception:
            text = text.decode('latin1')
            # save cookie jar
            save_cookie_jar(jar, COOKIE_PATH)
        return text, resp.info()
    except Exception as e:
        log('HTTP POST failed: %s' % str(e), xbmc.LOGERROR)
        raise

# --------------------- UI helpers ---------------------


def add_dir(params, list_label, info=None, art=None, is_folder=True):
    url = sys.argv[0] + '?' + urllib.urlencode(params)
    li = xbmcgui.ListItem(list_label)
    if info:
        li.setInfo('video', info)
    if art:
        try:
            li.setArt(art)
        except Exception:
            pass
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=is_folder)


# --------------------- plugin actions ---------------------


def show_root():
    add_dir({'action': 'search'}, 'Search')
    add_dir({'action': 'login'}, 'Login (save cookies)')
    add_dir({'action': 'clear_cookies'}, 'Clear cookies')
    xbmcplugin.endOfDirectory(HANDLE)

def do_login():
    # Ask username/password via keyboard dialogs
    kb = xbmcgui.Dialog()
    username = xbmcgui.Dialog().input('Username', type=xbmcgui.INPUT_ALPHANUM)
    if username is None:
        return
    password = xbmcgui.Dialog().input('Password', type=xbmcgui.INPUT_PASSWORD)
    if password is None:
        return
    
    
    payload = {'username': username, 'password': password}
    url = BASE_URL.rstrip('/') + API_LOGIN
    try:
        text, info = http_post_json(url, payload)
        # If response includes Set-Cookie, cookiejar already saved by http_post_json
        xbmcgui.Dialog().notification('Login', 'Login request sent', xbmcgui.NOTIFICATION_INFO)
        # show response message if JSON
        try:
            j = json.loads(text)
            if isinstance(j, dict) and j.get('ok') is not None:
                xbmcgui.Dialog().notification('Login', 'Server response: %s' % str(j), xbmcgui.NOTIFICATION_INFO)
        except Exception:
            pass
    except Exception as e:
        xbmcgui.Dialog().notification('Login failed', str(e), xbmcgui.NOTIFICATION_ERROR)

def clear_cookies():
    try:
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
            xbmcgui.Dialog().notification('Cookies', 'Cookies cleared', xbmcgui.NOTIFICATION_INFO)
    except Exception as e:
        xbmcgui.Dialog().notification('Error', str(e), xbmcgui.NOTIFICATION_ERROR)


def do_search(query=None):
    if not query:
        kb = xbmc.Keyboard('', 'Search videos')
        kb.doModal()
        if not kb.isConfirmed():
            return
        query = kb.getText()
    
    
    q = urllib.quote(query.encode('utf-8'))
    url = BASE_URL.rstrip('/') + API_SEARCH + '?q=' + q
    try:
        text, headers = http_get(url)
    except Exception as e:
        xbmcgui.Dialog().notification('Search failed', str(e), xbmcgui.NOTIFICATION_ERROR)
        return
    
    
    try:
        data = json.loads(text)
    except Exception as e:
        log('JSON parse failed: %s %s' % (e, text), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Invalid response', 'Cannot parse JSON', xbmcgui.NOTIFICATION_ERROR)
        return
    
    
    results = data.get('results', [])
    if not results:
        xbmcgui.Dialog().notification('No results', 'No results for %s' % query, xbmcgui.NOTIFICATION_INFO)
        return
    for item in results:
        title = item.get('title') or 'Untitled'
        year = item.get('year') or ''
        label = '%s (%s)' % (title, year) if year else title
        poster = item.get('poster')
        plot = item.get('desc') or ''
        info = {'title': title, 'plot': plot, 'genre': item.get('class') or '', 'year': year}
        params = {'action': 'list_episodes', 'item_json': urllib.quote(json.dumps(item))}
        art = {}
        if poster:
            art = {'thumb': poster, 'icon': poster, 'fanart': poster}
        add_dir(params, label, info=info, art=art, is_folder=True)
    
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_episodes(item_json):
    try:
        item = json.loads(urllib.unquote(item_json))
    except Exception as e:
        log('Failed to load item json: %s' % str(e), xbmc.LOGERROR)
        return
    
    
    title = item.get('title')
    poster = item.get('poster')
    episodes = item.get('episodes') or []
    episodes_titles = item.get('episodes_titles') or []
    plot = item.get('desc') or ''
    
    
    # Info entry
    info = {'title': title, 'plot': plot}
    add_dir({'action': 'info_only'}, title, info=info, art={'thumb': poster}, is_folder=False)
    
    
    for idx, url in enumerate(episodes):
        ep_title = episodes_titles[idx] if idx < len(episodes_titles) else 'Episode %d' % (idx+1)
        label = ep_title
        params = {'action': 'play', 'url': url}
        li = xbmcgui.ListItem(label)
        li.setInfo('video', {'title': title + ' - ' + ep_title, 'plot': plot})
        if poster:
            try:
                li.setArt({'thumb': poster, 'icon': poster, 'fanart': poster})
            except Exception:
                pass
        u = sys.argv[0] + '?' + urllib.urlencode(params)
        xbmcplugin.addDirectoryItem(HANDLE, u, li, isFolder=False)
    
    
    xbmcplugin.endOfDirectory(HANDLE)
def play_stream(url):
    try:
        li = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(HANDLE, True, li)
    except Exception as e:
        log('Play failed: %s' % str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Play failed', str(e), xbmcgui.NOTIFICATION_ERROR)

# --------------------- router ---------------------


def router():
    # parse args
    params = {}
    if len(sys.argv) > 2 and sys.argv[2]:
        params = dict(urlparse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    
    
    try:
        if action is None:
            show_root()
        elif action == 'login':
            do_login()
            show_root()
        elif action == 'clear_cookies':
            clear_cookies()
            show_root()
        elif action == 'search':
            # allow passing q as parameter
            q = params.get('q')
            do_search(q)
        elif action == 'list_episodes':
            item_json = params.get('item_json')
            if item_json:
                list_episodes(item_json)
            else:
                xbmcgui.Dialog().notification('Missing item', 'No item data provided', xbmcgui.NOTIFICATION_ERROR)
        elif action == 'play':
            url = params.get('url')
            if url:
                play_stream(url)
            else:
                xbmcgui.Dialog().notification('Missing url', 'No URL to play', xbmcgui.NOTIFICATION_ERROR)
        else:
            xbmcgui.Dialog().notification(
                'Unknown action',
                action,
                xbmcgui.NOTIFICATION_ERROR
            )
    except Exception as e:
        xbmcgui.Dialog().notification(
            'Router Error',
            str(e),
            xbmcgui.NOTIFICATION_ERROR
        )
