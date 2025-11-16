# coding: utf-8
import sys,os,json,traceback,urllib,cookielib, urllib2

try:
    from urllib import urlencode
    from urllib import quote,unquote
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import urlencode,quote,parse_qsl,unquote

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

BASE_URL = ADDON.getSetting('base_url') or 'http://127.0.0.1:3300'
API_SEARCH = '/api/search'
API_LOGIN = '/api/login'



# Cookie file path (Netscape format)
COOKIE_PATH = xbmc.translatePath('special://profile/addon_data/plugin.video.lunaTV/cookies.txt')
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
    jar = cookielib.LWPCookieJar()
    try:
        if os.path.exists(path):
            jar.load(path, ignore_discard=True, ignore_expires=True)
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

    data = json.dumps(payload)
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
        os.makedirs(folder)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(history[:MAX_HISTORY]))
        
def get_search_query():
    history = load_history()
    menu = ["➕ New search..."]
    if history:
        # show previous searches
        for h in history:
            menu.append("🔍 " + h)

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
        query = history[choice]

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
        label = '%s (%s)' % (title, year) if year else title
        poster = item.get('poster')
        plot = item.get('desc') or ''
        source = item.get('source_name') or ''
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
