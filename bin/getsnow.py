import os
import logging
import logging.handlers
import sys
import json
from platform import system
from splunk.clilib import cli_common as cli
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option

platform = system().lower()

# Lazy load python eggs. Loading eggs into python execution path
if platform == 'darwin':
    platform = 'macosx'
running_dir = os.path.dirname(os.path.realpath(__file__))
egg_dir = os.path.join(running_dir, 'eggs')
for filename in os.listdir(egg_dir):
    file_segments = filename.split('-')
    if filename.endswith('.egg'):
        filename = os.path.join(egg_dir, filename)
        if len(file_segments) <= 3:
            sys.path.append(filename)
        else:
            if platform in filename:
                sys.path.append(filename)

# lazy load requests module
import requests


def setup_logger(level):
    """
        :param level: Logging level
        :type level: logger object
        :return : logger object
    """
    os.environ['SPLUNK_HOME']
    logger = logging.getLogger('getsnow')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'getsnow.log'),
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
    """
    Returns dict object of config file settings
    :param conf: Splunk conf file name
    :param stanza: stanza (entry) from conf file
    :return: returns dictionary of setting
    """
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


@Configuration()
class getSnowCommand(GeneratingCommand):
    """ %(synopsis)

    ##Syntax
    .. code-block::
    getsnow filters="<key1>=<value1> <key2>=<value2>" daysAgo=<int> env=<str> table=<str>

    ##Description

    Returns json events for Service Now API from tables.  Limit 1000 events.

    ##Example

    Return json events where where active is true and contact_type is phone for the past 30 days.

    .. code-block::
        | getsnow filters="active=true contact_type=phone" daysAgo=30
        OR
        | getsnow filters="active=true contact_type=phone" glideSystem="beginningOfLastWeek()"

    """

    table = Option(
        doc='''**Syntax:** **table=***<str>*
        **Description:** sets which table to query. Default incident table.''',
        require=False)

    filters = Option(
        doc='''**Syntax:** **filters=***<str>*
        **Description:** list of key values where key and value are present. If no filters specified returns 1 event''',
        require=False)

    daysAgo = Option(
        doc='''**Syntax:** **poolOnly=***<int>*
        **Description:** Filter for number of days to return.  Limit of event still 1000. Default None''',
        require=False)

    glideSystem= Option(
        doc='''**Syntax:** **glideSystem=***<str>*
        **Description:** Allows use to pass any GlideSystem as defined by Service Now. It is up to the user to format 
        function.''',
        require=False)

    env = Option(
        doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
        require=False)

    def generate(self):
        # Parse and set arguments
        logger = setup_logger(logging.INFO)
        if self.daysAgo and self.glideSystem:
            record = dict()
            record['error'] = 'daysAgo and glideSystem defined.  Must define only one!'
            record['_raw'] = tojson(record)
            yield record
            exit()
        time_range = '^opened_at>=javascript:gs.daysAgo(%s)' % self.daysAgo if self.daysAgo else ''
        time_range = '^opened_at>=javascript:gs.%s' % self.glideSystem if self.glideSystem else time_range
        sysparam_query = '%s%s%s' % ('sysparm_query=', '^'.join(self.filters.split(',')), time_range) if self.filters else 'sysparm_limit=1'
        table = self.table if self.table else 'incident'
        env = self.env if self.env else 'production'

        try:
            # get config
            conf = getstanza('getsnow', env)
            proxy_conf = getstanza('getsnow', 'global')
            proxies = setproxy(conf, proxy_conf)
            user = conf['user']
            password = conf['password']
            url = conf['url']
            timeout = int(conf['timeout']) if 'timeout'in conf else 120
            # build url for with filters and table
            url = '%s%s%s%s%s' % (url, '/api/now/table/', table, '?', sysparam_query)
            # retrieving data from Service now API
            snow_request = requests.get(url, auth=(user, password), headers={'Accept': 'application/json'},
                                        timeout=timeout, proxies=proxies)
            records = snow_request.json()
        except Exception as e:
            logger.debug('getSnowCommand: %s' % e)
            yield {'error': e, '_raw': e}
            exit()

        if snow_request.status_code == 200:
            # for each event creating dic object for yield
            for record in records['result']:
                record = dictexpand(record)
                record['_raw'] = tojson(record)
                yield record
        else:
            try:
                # If not 200 status_code showing error message in Splunk UI
                record = dictexpand(records)
                record['url'] = url
                record['_raw'] = tojson(records)
            except Exception as e:
                record = dict()
                record['url'] = url
                record['error'] = e
            yield record
        exit()

dispatch(getSnowCommand, sys.argv, sys.stdin, sys.stdout, __name__)