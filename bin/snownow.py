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
import sys
import ast
from snowpy import snow
from logging import INFO
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option


logger = util.setup_logger(INFO)

@Configuration(local=True)
class snowNowCommand(GeneratingCommand):
    """ %(synopsis)

    ##Syntax
    .. code-block::
    getsnow filters="<key1>=<value1> <key2>=<value2>" daysAgo=<int> env=<str> table=<str>

    ##Description

    Returns json events for Service Now API from tables.  Limit 1000 events.

    ##Example

    Return json events where where active is true and contact_type is phone for the past 30 days.

    .. code-block::
        | snownow filters="active=true,contact_type=phone" daysAgo=30
        OR
        | snownow filters="active=truecontact_type=phone" limit=10000"

    """

    table = Option(
        doc='''**Syntax:** **table=***<str>*
        **Description:** sets which table to query. Default incident table.''',
        require=True)

    filters = Option(
        doc='''**Syntax:** **filters=***<str>*
        **Description:** list of key values where key and value are present. If no filters specified returns 1 event''',
        require=False)

    limit = Option(
        doc='''**Syntax:** **filters=***<str>*
        **Description:** Maximium number of records in batches of 10,000''',
        require=True)

    daysAgo = Option(
        doc='''**Syntax:** **poolOnly=***<int>*
        **Description:** Filter for number of days to return.  Limit of event still 1000. Default None''',
        require=False)

    env = Option(
        doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
        require=False)

    def generate(self):
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        #proxy_conf = util.getstanza('getsnow', 'global')
        #proxies = util.setproxy(conf, proxy_conf)
        username = conf['user']
        password = conf['password']
        url = conf['url']
        value_replacements = conf['value_replacements']
        daysAgo = self.daysAgo
        daysBy = self.daysAgo
        filters = self.filters
        table = self.table
        limit = self.limit
        bfilter = {}
        filters = filters.split(',') if filters else []
        exuded = []
        for x in filters:
            k, v = x.split('=')
            if k in bfilter:
                bfilter[k].append(v)
            else:
                bfilter[k] = []
                bfilter[k].append(v)
        snownow = snow(url, username, password)
        snownow.replacementsdict(value_replacements)
        for k, v in bfilter.iteritems():
            exuded.append(snownow.filterbuilder(k, v))
        url = snownow.reqencode(exuded, table=table, timeby=daysBy, days=daysAgo)
        for record in snownow.getrecords(url, limit):
            # record = snownow.updaterecord(record, sourcetype='snow', lookup=True)
            record = snownow.updatevalue(record, sourcetype='snow')
            record['_raw'] = util.tojson(record)
            yield record

dispatch(snowNowCommand, sys.argv, sys.stdin, sys.stdout, __name__)
