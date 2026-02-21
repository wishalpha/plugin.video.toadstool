# coding: utf-8
import sys, os, json, traceback, io
import urllib.request as urllib2
import urllib.parse as urllib
import http.cookiejar as cookielib

# These are now all located in urllib.parse
from urllib.parse import urlencode, quote, unquote, parse_qsl

import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
import xbmcaddon

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

BASE_URL = ADDON.getSetting('base_url') or 'http://192.168.1.1:3300'
API_SEARCH = '/api/search'
API_LOGIN = '/api/login'



# Cookie file path (Netscape format)
COOKIE_PATH = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.lunaTV/cookies.txt')
HTTP_TIMEOUT = 20

def get_user_input():  
    kb = xbmc.Keyboard('', 'Please enter the video title')
    kb.doModal() # Onscreen keyboard appears
    if not kb.isConfirmed():
        return
    query = kb.getText() # User input
    return query

def get_ip():  
    file_path='server_list'
    server_list = ['127.0.0.1','192.168.1.253']
    #with open(file_path, 'r') as file:
    #    for line in file:
    #        server_list.append(line.strip())
    ip_index= xbmcgui.Dialog().contextmenu(list=['new']+server_list)
    if ip_index == 0:
        kb = xbmc.Keyboard('192.168.1.1', 'Please enter server ip')
        kb.doModal() # Onscreen keyboard appears
        if not kb.isConfirmed():
            return '192.168.1.253'
        query = kb.getText() # User input
    #    with open(file_path, 'a') as file:
    #        file.write(query+'\n')
        return query
    return server_list[ip_index-1]
def to_text (url_string):
    return unquote(url_string)
def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))
def get_home():
    return CATEGORIES


# --------------------- logging ---------------------
def log(msg, level=xbmc.LOGINFO):
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
    # Ensure path is a real OS path
    translated_path = xbmcvfs.translatePath(path)
    
    jar = cookielib.LWPCookieJar()
    try:
        # Use xbmcvfs.exists for better compatibility in Kodi
        if xbmcvfs.exists(translated_path):
            # Check if file is not empty to avoid Python 3 LoadError
            if os.path.getsize(translated_path) > 0:
                jar.load(translated_path, ignore_discard=True, ignore_expires=True)
                log('Loaded cookies from %s' % translated_path)
            else:
                log('Cookie file empty, skipping load', xbmc.LOGINFO)
    except Exception as e:
        log('Failed loading cookies: %s' % str(e), xbmc.LOGWARNING)
    return jar

def save_cookie_jar(jar, path):
    try:
        translated_path = xbmcvfs.translatePath(path)
        jar.save(translated_path, ignore_discard=True, ignore_expires=True)
        log('Saved cookies to %s' % translated_path)
    except Exception as e:
        log('Failed saving cookies: %s' % str(e), xbmc.LOGERROR)

# --------------------- HTTP helpers ---------------------


def build_opener(cookiejar=None):
    if cookiejar is None:
        cookiejar = load_cookie_jar(COOKIE_PATH)
        handler = urllib2.HTTPCookieProcessor(cookiejar)
        opener = urllib2.build_opener(handler)
        #opener.addheaders = [('User-agent', 'Kodi-dytt-search/1.0')]
    return opener, cookiejar




def http_get(url):
    opener, jar = build_opener()
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    req = urllib2.Request(url, None, headers)
    try:
        resp = opener.open(req, timeout=HTTP_TIMEOUT)
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

    data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Content-Length': str(len(data)),
        'User-Agent': 'Mozilla/5.0'
    }

    req = urllib2.Request(url, data, headers)

    try:
        resp = opener.open(req, timeout=HTTP_TIMEOUT)
        text = resp.read()

        # decode
        try:
            text = text.decode('utf-8')
        except:
            text = text.decode('latin1')

        # save cookies
        save_cookie_jar(jar, COOKIE_PATH)
        return text, resp.info()

    except Exception as e:
        log('HTTP POST failed: %s' % str(e), xbmc.LOGERROR)
        raise


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
    xbmcplugin.addDirectoryItem(_handle, url, li, isFolder=is_folder)

def ensure_unicode(s):
    if isinstance(s, unicode):
        return s
    try:
        return s.decode('utf-8')
    except:
        return s.decode('latin1')
HISTORY_FILE = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.lunaTV/search_history.txt")
MAX_HISTORY = 20

def load_history():
    # Use translated path for Kodi compatibility
    path = xbmcvfs.translatePath(HISTORY_FILE)
    
    if os.path.exists(path):
        # Open in text mode with explicit encoding
        with open(path, "r", encoding="utf-8") as f:
            # No need to .decode() here; f.readlines() returns strings
            return [line.strip() for line in f.readlines()]
    else:
        # Python 3 strings are already unicode, 'u' prefix is optional
        DEFAULT_HISTORY = ["海底小纵队", "小猪佩奇"]
        save_history(DEFAULT_HISTORY)
        return list(DEFAULT_HISTORY)

def save_history(history):
    path = xbmcvfs.translatePath(HISTORY_FILE)
    folder = os.path.dirname(path)
    
    if not os.path.exists(folder):
        os.makedirs(folder)
        
    # Open in text mode with explicit encoding
    with open(path, "w", encoding="utf-8") as f:
        data = "\n".join(history[:MAX_HISTORY])
        # Write the string directly; do NOT .encode() it
        f.write(data)


def get_search_query():
    history = load_history()
    xbmc.log("Loaded history: %s" % [h.encode("utf-8") for h in history], level=xbmc.LOGNOTICE)
    menu = ["New search..."]
    if history:
        # show previous searches
        for h in history:
            menu.append(h)

    choice = xbmcgui.Dialog().select("Search History", menu)

    # user cancelled
    if choice < 0:
        return None

    # chose "new search"
    if choice == 0:
        kb = xbmc.Keyboard('', 'Keywords')
        kb.doModal()
        if not kb.isConfirmed():
            return None
        query = kb.getText()
    else:
        # selected old history item
        query = history[choice-1]
    try:
        unicode  # Python 2: exists
        if isinstance(query, bytes):
            query = query.decode("utf-8", "ignore")
    except NameError:
        # Python 3: nothing to do
        pass
    # update history
    if query:
        # put new query always at top
        if query in history:
            history.remove(query)
        history.insert(0, query)

        save_history(history)

    return query

def do_search():

    query = get_search_query()
    
    query_u = ensure_unicode(query)
    q = urllib.urlencode({'q': query_u.encode('utf-8')})
    url = BASE_URL.rstrip('/') + API_SEARCH + '?' + q
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
        source = item.get('source_name') or ''
        if year and source:
            label = "%s (%s)-(%s)" % (title, year, source)
        elif year:
            label = "%s (%s)" % (title, source)
        elif source:
            label = "%s (%s)" % (title, year)
        else:
            label = title
        poster = item.get('poster')
        plot = item.get('desc') or ''
        
        info = {'title': title+'('+source+')' , 'plot': plot, 'genre': item.get('class') or '', 'year': year}
        params = {'action': 'list_episodes', 'item_json': urllib.quote(json.dumps(item))}
        art = {}
        if poster:
            art = {'thumb': poster, 'icon': poster, 'fanart': poster}
        add_dir(params, label, info=info, art=art, is_folder=True)
    
    
    xbmcplugin.endOfDirectory(_handle)

def home_list():
    add_dir({'action': 'search'}, 'Search')
    add_dir({'action': 'login'}, 'Login (save cookies)')
    add_dir({'action': 'logout'}, 'Clear cookies')
    xbmcplugin.endOfDirectory(_handle)

def do_login():
    # Ask username/password via keyboard dialogs
    #kb = xbmcgui.Dialog()
    #username = xbmcgui.Dialog().input('Username', type=xbmcgui.INPUT_ALPHANUM)
    #if username is None:
    #    return
    #password = xbmcgui.Dialog().input('Password', type=xbmcgui.INPUT_PASSWORD)
    #if password is None:
    #   return
    
    
    payload = {'username': 'admin', 'password': '1qaz2wsx'}
    url = BASE_URL.rstrip('/') + API_LOGIN
    print(url)
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
        u = "%s?action=play&url=%s" % (_url, url)
        msg = "Episode {} URL: {}".format(idx+1, url)
        xbmc.log(msg.encode('utf-8'), xbmc.LOGINFO)
        xbmcplugin.addDirectoryItem(_handle, u, li, isFolder=False)
    
    
    xbmcplugin.endOfDirectory(_handle)

def clear_cookies():
    try:
        if os.path.exists(COOKIE_PATH):
            os.remove(COOKIE_PATH)
            xbmcgui.Dialog().notification('Cookies', 'Cookies cleared', xbmcgui.NOTIFICATION_INFO)
    except Exception as e:
        xbmcgui.Dialog().notification('Error', str(e), xbmcgui.NOTIFICATION_ERROR)


def play_video(path):
    try:
        # Safe UTF-8 logging
        log_msg = "LunaTV: Playing URL: {}".format(path)
        xbmc.log(log_msg.encode("utf-8"), xbmc.LOGINFO)

        play_item = xbmcgui.ListItem(path=path)
        play_item.setProperty('IsPlayable', 'true')
        
        # This tells Kodi to use InputStream Adaptive
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        
        # Specify the type of manifest (HLS or DASH)
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')  # or 'mpd' for DASH

        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

    except Exception as e:
        err = "LunaTV: Play failed: {}".format(e)
        xbmc.log(err.encode("utf-8"), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Play failed', str(e), xbmcgui.NOTIFICATION_ERROR)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'search':
            # Display the list of videos in a provided category.
            do_search()
        elif params['action'] == 'login':
            # Display the list of videos in a provided category.
            do_login()
            home_list()
        elif params['action'] == 'logout':
            # Display the list of videos in a provided category.
            clear_cookies()
            home_list()  
            #home_xiaoya('dav://admin:root@{}:5244'.format(get_ip()))

        elif params['action'] == 'list_episodes':

            list_episodes(params["item_json"])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            #xbmc.log('Playing :'+to_text(params['video']),xbmc.LOGERROR)
            play_video(params['url'])  
        elif params['action'] == 'home':
            # Play a video from a provided URL.
            home_list()
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        home_list()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
