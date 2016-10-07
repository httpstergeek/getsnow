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
from urllib import quote_plus
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
        self._api = '{}/api/now/table/{}?{}sysparm_query={}&sysparm_display_value=true{}'
        self.connect = self._connect

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
        """
        :rtype dict:
        :param record:
        :param field:
        :param destfield:
        :return:
        """
        if destfield:
            timeobject = dt.strptime(record[field],"%Y-%m-%d %H:%M:%S").timetuple()
            record[destfield] = time.mktime(timeobject) if field in record else ''
        return record

    @staticmethod
    def filterbuilder(filter, filterarg):
        """
        :rtype: string:
        :param filter:
        :param filterarg:
        :return:
        """
        if filterarg:
            filterarg = [filter.strip() + '=' + quote_plus(x) for x in filterarg if x]
            filterarg = '^OR'.join(filterarg)
        else:
            filterarg = ''
        return filterarg

    def getsysid(self, table, key, values):
        """
        Retrieves sys_id from Service Now Table where key values match
        :rtype list:
        :param table: str - Service Now table
        :param key: str - key in Service Now record to match values
        :param values: list - values to match
        :return:
        """
        sysid = []
        if values:
            filters = self.filterbuilder(key, values)
            query_string = self.reqencode([filters], table)
            for record in self.getrecords(query_string):
                if record['sys_id']:
                    sysid.append(str(record['sys_id']))
        return sysid

    def getrecords(self, url, limit=None):
        """
        :param url: string
        :param limit: int
        :return:
        """
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

    def reqencode(self, sysparm_query, table=None, glide_system=None, active=None, sysparm_limit=None, sysparm_fields=None):
        """
        Creates Service Now api url
        :rtype: str
        :param filters: string
        :param table: string
        :param glide_system: string
        :param active: boolean
        :param sysparm_limit: int
        :param sysparm_fields: list
        :return:
        """
        query = [sysparm_query]
        active = 'active={}'.format(active).lower() if active else ''
        sysparm_limit = 'sysparm_limit={}&'.format(sysparm_limit) if sysparm_limit else ''
        glide_system = glide_system if glide_system else ''
        sysparm_fields = '&sysparm_fields={}'.format('%2C'.join(sysparm_fields)) if sysparm_fields else ''
        query.insert(0, glide_system)
        query.append(active)
        query = [x for x in query if x]
        sysparm_query = self._api.format(self.url, table, sysparm_limit, '^'.join(query), sysparm_fields)
        return sysparm_query

    def updaterecord(self, record, sourcetype='snow'):
        """
        Updates Service Now sys_id with value for record links, _time, source, and sourcetype
        :rtype: dict
        :param record: dict - single Service Now record
        :param sourcetype:  str - sourcetype for Splunk
        :return:
        """
        record['sourcetype'] = sourcetype
        record['source'] = self.lasturl
        record = self.updatetime(record, 'sys_created_on', '_time')
        return record

    def updatevalue(self, record, sourcetype='snow'):
        #for k, v in record.iteritems():
        #    if isinstance(v, dict):
        #        record[k] = v['value']
        record['sourcetype'] = sourcetype
        record['source'] = self.lasturl
        record = self.updatetime(record, 'sys_created_on', '_time')
        return record

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
            if v:
                v = str(v)
                pdict[k] = v
            else:
                pdict[k] = "null"
                pdict[k+'.display_value'] = "null"
                pdict[k+'.link'] = "null"
    return pdict
