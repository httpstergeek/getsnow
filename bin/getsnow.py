# encoding: utf-8
# Author: Bernardo Macias <bmacias@httpstergeek.com>
#
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

import util
import json
import sys
import time
import datetime
from logging import INFO
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option


logger = util.setup_logger(INFO)


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
        logger = util.setup_logger(INFO)
        if self.daysAgo and self.glideSystem:
            record = dict()
            record['error'] = 'daysAgo and glideSystem defined.  Must define only one!'
            record['_raw'] = tojson(record)
            yield record
            exit()

        # get config
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        proxy_conf = util.getstanza('getsnow', 'global')
        proxies = util.setproxy(conf, proxy_conf)
        username = conf['user']
        password = conf['password']
        release = conf['release']
        url = conf['url']
        timeout = int(conf['timeout']) if 'timeout'in conf else 120

        # building query string
        time_range = '^opened_at>=javascript:gs.daysAgo(%s)' % self.daysAgo if self.daysAgo else ''
        time_range = '^opened_at>=javascript:gs.%s' % self.glideSystem if self.glideSystem else time_range
        sysparam_query = '?sysparm_display_value=all%s%s%s' % ('&sysparm_query=', '^'.join(self.filters.split(',')), time_range) if self.filters else 'sysparm_limit=1'
        sysparam_query = sysparam_query.replace(' ', '%20')

        # changing URL for Fuji
        if release == 'Fuji':
            sysparam_query = sysparam_query.replace('&sysparm_query=', '&')
            sysparam_query = sysparam_query.replace('^', '&')

        table = self.table if self.table else 'incident'
        # build url for with filters and table
        url = '%s/api/now/table/%s%s' % (url, table, sysparam_query)
        logger.info('request query: %s' % url)

        try:
            # retrieving data from Service now API
            records = util.request(url,
                                   username=username,
                                   password=password,
                                   headers={'Accept': 'application/json'},
                                   timeout=timeout,
                                   proxy=proxies)
        except Exception as e:
            logger.debug('getSnowCommand: %s' % e)
            yield {'error': e, '_raw': e, 'url': url}
            exit()

        if records['code'] == 200:
            records = json.loads(records['msg'])
            # for each event creating dic object for yield
            for record in records['result']:
                dates = list()
                dates.append({'sys_created_on.epoch': record['sys_created_on']['display_value']})
                dates.append({'_time': record['sys_created_on']['display_value']})
                dates.append({'resolved_at.epoch': record['resolved_at']['display_value']})
                dates.append({'sys_updated_on.epoch': record['sys_updated_on']['display_value']})
                for date in dates:
                    for key, value in date.iteritems():
                        if value:
                            record[key] = time.mktime(datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timetuple())
                record = util.dictexpand(record)
                record['_raw'] = util.tojson(record)
                yield record
        else:
            try:
                # If not 200 status_code showing error message in Splunk UI
                record = util.dictexpand(records)
                record['url'] = url
                record['_raw'] = util.tojson(records)
            except Exception as e:
                record = dict()
                record['url'] = url
                record['error'] = e
                record['_raw'] = util.tojson(record)
            yield record
        exit()

dispatch(getSnowCommand, sys.argv, sys.stdin, sys.stdout, __name__)