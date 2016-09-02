#
# All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'Bernardo Macias '
__credits__ = ['Bernardo Macias']
__license__ = "ASF"
__version__ = "2.0"
__maintainer__ = "Bernardo Macias"
__email__ = 'bmacias@httpstergeek.com'
__status__ = 'Production'

import os
try:
    from splunk.clilib import cli_common as cli
except:
    pass
import json
import base64
import urllib
import urllib2
import logging
import logging.handlers


def setup_logger(level):
    """
    setups logger
    :param level: Logging level
    :return: logger object
    """
    appname = os.path.dirname(os.path.realpath(__file__)).split('/')[-2]
    logger = logging.getLogger(appname)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ['SPLUNK_HOME'],
                                                                     'var',
                                                                     'log',
                                                                     'splunk',
                                                                     '{0}.log'.format(appname)),
                                                        maxBytes=5000000,
                                                        backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(formatter)
    logger.addHandler(consolehandler)
    return logger


def getstanza(conf, stanza):

    appdir = os.path.dirname(os.path.dirname(__file__))
    conf = "%s.conf" % conf
    apikeyconfpath = os.path.join(appdir, "default", conf)
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", conf)
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]


def setproxy(local_conf, global_conf):
    """
    Sets up dict object for proxy settings
    :param local_conf:
    :param global_conf:
    :return:
    """
    proxy = None
    proxy_url = global_conf['proxy_url'] if 'proxy_url' in global_conf else None
    proxy_url = local_conf['proxy_url'] if 'proxy_url' in local_conf else proxy_url
    if proxy_url:
        proxy = dict()
        proxy_user = global_conf['proxy_user'] if 'proxy_user' in global_conf else None
        proxy_user = local_conf['proxy_user'] if 'proxy_user' in local_conf else proxy_user
        proxy_password = global_conf['proxy_password'] if 'proxy_password' in global_conf else None
        proxy_password = local_conf['proxy_password'] if 'proxy_password' in local_conf else proxy_password
        if proxy_password and proxy_user:
            proxy_url = '%s:%s@%s' % (proxy_user, proxy_password, proxy_url)
        elif proxy_user and not proxy_password:
            proxy_url = '%s@%s' % (proxy_user, proxy_url)
        elif not proxy_user and not proxy_password and proxy_url:
            proxy_url = '%s' % proxy_url
        else:
            proxy = None
        if proxy:
            proxy['https'] = 'https://%s' % proxy_url
            proxy['http'] = 'http://%s' % proxy_url
    return proxy


def dictexpand(item, key=None):
    """
    Flattens dictionary of dictionary using key from parent
    :param item: dict object
    :param key: key from parent
    :return: dict
    """
    pdict = dict()
    for k, v in item.iteritems():
        if key:
            k = "%s.%s" % (key, k)
        if isinstance(v, dict):
            cdict = dictexpand(v, k)
            pdict = dict(pdict.items() + cdict.items())
        else:
            v = str(v)
            pdict[k] = v
    return pdict


def tojson(jmessage):
    """
    Returns a pretty print json string
    :param jmessage: dict object
    :return: str
    """
    jmessage = json.dumps(json.loads(json.JSONEncoder().encode(jmessage)),
                          indent=4,
                          sort_keys=True,
                          ensure_ascii=True)
    return jmessage


def request(url, username=None, password=None, headers=None, data=None, proxy=None, timeout=None):
    """
    :param url: string, http(s)://
    :param username:
    :param password:
    :param headers:
    :param data:
    :param proxy: dict object ProxyHandler
    :param timeout:
    :return:
    """
    if proxy:
        if ('http' in proxy) or ('https' in proxy):
            proxy_handler = urllib2.ProxyHandler(proxy)
            proxy_auth_handler = urllib2.ProBasicAuthHandler()
            build_opener = urllib2.build_opener(proxy_handler, proxy_auth_handler, urllib2.HTTPHandler)
            urllib2.install_opener(build_opener)
        else:
            raise KeyError("http or https not found in proxy settings")

    url_encode = urllib.urlencode(data) if data else None
    connection = urllib2.Request(url, data=url_encode, headers=headers)
    if username and password:
        encoded = base64.encodestring('{0}:{1}'.format(username, password)).strip()
        connection.add_header("Authorization", "Basic %s" % encoded)
    try:
        response = urllib2.urlopen(connection, timeout=timeout)
        response = dict(code=response.getcode(), msg=response.read(), headers=response.info())
    except urllib2.URLError, e:
        response = dict(code=e.code, msg=e.reason, url=url)
    except Exception:
        import traceback
        response = dict(code=None, msg=traceback.format_exc())
    return response