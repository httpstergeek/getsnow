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
import time
import datetime
import requests
import sys
import copy
from logging import INFO
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option


logger = util.setup_logger(INFO)

@Configuration(local=True, type='eventing', retainsevents=True, streaming=False)
class snowTaskCommand(GeneratingCommand):
    """ %(synopsis)

    ##Syntax
    .. code-block::
    getuser env=<str> user_name=<str> daysAgo=<int> env=<str>

    ##Description

    Returns json events for Service Now API from tables.  Limit 1000 events.

    ##Example

    Return json events where where active is true and contact_type is phone for the past 30 days.

    .. code-block::
        | getsnow user_name=rick daysAgo=30
        OR
        | getsnow env=production user_name=mortey

    """

    user_names = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** user_name of user''',
            require=False)
    assignment_groups = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** assignment_group incident assigned to ticket''',
            require=False)
    filterby = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** assignment_group incident assigned to ticket''',
            require=False)

    daysAgo = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    daysby = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    active = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    limit = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    env = Option(
            doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
            require=False)

    def generate(self):
        # Parse and set arguments

        # get config
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        proxy_conf = util.getstanza('getsnow', 'global')
        username = conf['user']
        password = conf['password']
        active = 'true'
        value_replacements = conf['value_replacements'].split(',') if conf['value_replacements'] else []
        user_names = self.user_names
        assigment_groups = self.assignment_groups
        filterby = self.filterby if self.filterby else 'assigned_to'
        limit = self.limit.lower() if self.limit else 'true'
        url = conf['url']
        limit = limit if limit == 'true' else 'else'
        if active:
            active = active if active == 'false' else 'true'
            active = 'active=%s' % active

        retrived_objects = {'user':{}, 'group': {}}

        replaces =[]
        user_sysid=''
        group_sysid=''

        def keyreplace(record, keyto, keyfrom, username, password):
            if keyto in record:
                if 'value' in record[keyto]:
                    value = record[keyto]['value']
                    if value == 'system':
                        record[keyto] = 'system'
                    else:
                        if value in retrived_objects:
                            record[keyto] = retrived_objects[value]
                        else:
                            response = requests.get(record[keyto]['link'],
                                                    auth=(username, password),
                                                    headers={'Accept': 'application/json'}
                                                    )
                            if response.status_code == 200:
                                usern = response.json()['result'][keyfrom]
                                record[keyto] = usern
                                retrived_objects[value] = usern
            return record

        def updatetime(record ,field, destfield=None):
            if not destfield:
                destfield = field
            record[destfield] = time.mktime(datetime.datetime.strptime(record[field],"%Y-%m-%d %H:%M:%S").timetuple()) if record['sys_created_on'] else ''
            return record

        def filterbuilder(filter, filterarg):
            if filterarg:
                filterarg = filterarg.split(',')
                filterarg = [filter.strip() + '='+x.strip() for x in filterarg if x]
                filterarg = '^OR'.join(filterarg).replace(' ', '%20')
            else:
                filterarg = ''
            return filterarg


        def getRecords(url, auth=None, limit=None):
            while url:
                response = requests.get(url,
                                        auth=(auth['user'], auth['password']),
                                        headers={'Accept': 'application/json'}
                                        )
                headers = response.headers
                source = copy.copy(url)
                xcount = headers['X-Total-Count'] if 'X-Total-Count' in headers else ''
                if 'Link' in headers:
                    links = headers['Link'].split(',')
                    for link in links:
                        if 'rel="next"' in link:
                            url = link.split(';')[0][1:-1]
                            break
                        else:
                            url = None
                else:
                    url = None
                if response.status_code == 200:
                    results = response.json()
                    if 'result' in results:
                        for result in results['result']:
                            result['X-Total-Count'] = xcount
                            result['source'] = source
                            yield result

        # user defined value replacements for keys with sys_id and links
        for value_replacement in value_replacements:
            if '=' in value_replacement:
                k,v = value_replacement.split('=')
                replaces.append({'tokey':k, 'fromkey':v})

        if user_names:
            filterarg = ''
            params = filterbuilder('user_name', user_names)
            query_string = '%s/api/now/table/%s?sysparm_query=%s' % (url,'sys_user', params)
            for record in getRecords(query_string, {'user': username, 'password': password}):
                if record['sys_id']:
                    retrived_objects['user'][record['sys_id']] = record['user_name']
                    filterarg = record['sys_id'] if not filterarg else ','.join([filterarg, record['sys_id']])
            user_sysid = filterbuilder(filterby, filterarg) if filterarg else ''

        if assigment_groups:
            filterarg = ''
            params = filterbuilder('name', assigment_groups)
            query_string = '%s/api/now/table/%s?sysparm_query=%s' % (url,'sys_user_group', params)
            for record in getRecords(query_string, {'user':username, 'password':password}):
                if record['sys_id']:
                    retrived_objects['group'][record['sys_id']] = record['name']
                    filterarg = record['sys_id'] if not filterarg else ','.join([filterarg, record['sys_id']])
            group_sysid = filterbuilder('assignment_group', filterarg) if filterarg else ''

        sysparm_query = [active, group_sysid, user_sysid]
        sysparm_query = [x for x in sysparm_query if x]
        sysparm_query = '^'.join(sysparm_query) if sysparm_query else ''
        sysparm_query = '&sysparm_query=' + sysparm_query


        query_string = '%s/api/now/table/%s?sysparm_limit=2000%s' % (url, 'sc_task', sysparm_query)

        retrived_objects = dict(retrived_objects['user'].items() + retrived_objects['group'].items())
        for record in getRecords(query_string, {'user': username, 'password':password}, limit=limit):
            for replace in replaces:
                record = keyreplace(record, replace['tokey'], replace['fromkey'], username, password)
            record['sourcetype'] = 'snow:incident'
            record['_raw'] = util.tojson(record)
            record = updatetime(record,'sys_created_on', '_time')
            yield record
        else:
            record = {'Warn': 'Records not found'}
            record['_raw'] = util.tojson(record)
            yield record
        exit()

dispatch(snowTaskCommand, sys.argv, sys.stdin, sys.stdout, __name__)