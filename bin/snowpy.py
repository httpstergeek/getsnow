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

import requests
import time
import re
import ast
import json
from datetime import datetime as dt
from copy import copy as cp

class snow:
    """
    Connects to Service Now API
    """
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.lasturl = None
        self._query = '{}/api/now/table/{}?{}sysparm_query={}'
        self.connect = self._connect
        self.replacements = {}
        self.sysidLookup = {}

    def _connect(self, url, username=None, password=None):
        """
        Sends a GET request
        :rtype: object
        :param url:
        :param username:
        :param password:
        :return:
        """
        username = username if username else self.username
        password = password if password else self.password
        response = requests.get(url,
                                auth=(username, password),
                                headers={'Accept': 'application/json'}
                                )
        return response

    @staticmethod
    def updatetime(record, field, destfield=None):
        if destfield:
            timeobject = dt.strptime(record[field],"%Y-%m-%d %H:%M:%S").timetuple()
            record[destfield] = time.mktime(timeobject) if field in record else ''
        return record

    @staticmethod
    def filterbuilder(filter, filterarg):
        """

        :rtype: string
        """
        if filterarg:
            filterarg = [filter.strip() + '='+x.strip() for x in filterarg if x]
            filterarg = '^OR'.join(filterarg).replace(' ', '%20')
        else:
            filterarg = ''
        return filterarg

    def getsysid(self, table, key, values, mapto=None):
        """
        Retrieves sys_id from Service Now Table where key values match
        :rtype: list
        :param table: str - Service Now table
        :param key: str - key in Service Now record to match values
        :param values: list - values to match
        :param mapto: string - key in lookup link to store for future lookups
        :return:
        """
        sysid = []
        user_records = []
        if values:
            exuded = self.filterbuilder(key, values)
            query_string = self.reqencode([exuded], table=table)
            for record in self.getrecords(query_string):
                if record['sys_id']:
                    if mapto:
                        self.sysidLookup[record['sys_id']] = record[mapto]
                    sysid.append(str(record['sys_id']))
                    user_records.append(record)
        return [sysid, user_records]

    def getrecords(self, url, username=None, password=None, limit=None):
        while url:
            response = self._connect(url)
            headers = response.headers
            source = cp(url)
            self.lasturl = source
            xcount = headers['X-Total-Count'] if 'X-Total-Count' in headers else ''
            if 'Link' in headers:
                links = headers['Link'].split(',')
                for link in links:
                    if 'rel="next"' in link:
                        url = link.split(';')[0][1:-1]
                        break
                    else:
                        url = None
                try:
                    limit = ast.literal_eval(limit)
                except:
                    limit = 0
                if limit != 0:
                    nextbatch = re.search('sysparm_offset=([^?>\s]+)', url)
                    nextbatch = int(nextbatch.group(1)) if nextbatch else 0
                    if xcount > 10000 or nextbatch > limit:
                        url = None
            else:
                url = None
            if response.status_code == 200:
                results = response.json()
                if 'result' in results:
                    for result in results['result']:
                        if xcount:
                            result['X-Total-Count'] = xcount
                        result['source'] = source
                        yield result

    def replacementsdict(self, lookupvalues):
        """
        Creates a dict from string e.i 'assigned_to=user_name, assignment_group=name' used by valuesreplace
        :param lookupvalues:
        :return:
        """
        lookupvalues = lookupvalues.split(',')
        for lookupvalue in lookupvalues:
            if '=' in lookupvalue:
                k, v = lookupvalue.strip().split('=')
                self.replacements[k] = v
        return self.replacements

    def reqencode(self, filters, table='incident', timeby='sys_created_on', active=None, days=None, sysparm_limit=None):
        """
        Creates Service Now api url
        :rtype: str
        :param filters: list
        :param table: string
        :param timeby: string
        :param active: boolean
        :param days: int
        :param sysparm_limit: int
        :return:
        """
        time_range = '{}>=javascript:gs.daysAgo({})'.format(timeby, days) if days else ''
        active = 'active={}'.format(active).lower() if active else ''
        sysparm_limit = str(sysparm_limit) if sysparm_limit else ''
        filters.insert(0, time_range)
        filters.append(active)
        filters = [x for x in filters if x]
        filters = '^'.join(filters)
        print table
        sysparm_limit = '{}&'.format(sysparm_limit) if sysparm_limit else ''
        sysparm_query = self._query.format(self.url, table, sysparm_limit, filters)
        return sysparm_query

    def updaterecord(self, record, sourcetype='snow',lookup=False):
        """
        Updates Service Now sys_id with value for record links, _time, source, and sourcetype
        :rtype: dict
        :param record: dict - single Service Now record
        :param sourcetype:  str - sourcetype for Splunk
        :param lookup:  bool - lookup sysid disabled
        :return:
        """
        if lookup:
            for k, v in self.replacements.iteritems():
                record = self.valuesreplace(record, k, v)
        record['sourcetype'] = sourcetype
        record['source'] = self.lasturl
        record = self.updatetime(record, 'sys_created_on', '_time')
        return record

    def valuesreplace(self, record, keyto, keyfrom):
        """
        Retrieves lookup link and replaces sys_id with value from lookup link.
        :rtype: dict
        :param record: dict - single Service Now record
        :param keyfrom: str - sys_id link lookup key
        :param keyto: str - key in Service Now record containing link
        :return:
        """
        if keyto in record:
            if 'value' in record[keyto]:
                sysid = record[keyto]['value']
                if sysid == 'system':
                    record[keyto] = 'system'
                else:
                    if sysid in self.sysidLookup:
                        record[keyto] = self.sysidLookup[sysid]
                    else:
                        if 'link' in record[keyto]:
                            response = self._connect(record[keyto]['link'])
                            if response.status_code == 200:
                                try:
                                    value = response.json()['result'][keyfrom]
                                    record[keyto] = value
                                    self.sysidLookup[sysid] = value
                                except Exception as e:
                                    pass
        return record

    def updatevalue(self, record, sourcetype='snow'):
        for k, v in record.iteritems():
            if isinstance(v, dict):
                record[k] = v['value']
        record['sourcetype'] = sourcetype
        record['source'] = self.lasturl
        record = self.updatetime(record, 'sys_created_on', '_time')
        return record
