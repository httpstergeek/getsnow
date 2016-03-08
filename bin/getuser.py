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

retrived_objects = {}

def keyreplace(record, keyto, keyfrom, username, password):
    if 'value' in record[keyto]:
        value = record[keyto]['value']
        if value in retrived_objects:
            record[keyto] = retrived_objects[value]
        else:
            response = util.request(record[keyto]['link'],
                                    username=username,
                                    password=password,
                                    headers={'Accept': 'application/json'}
                                    )
            usern = json.loads(response['msg'])['result'][keyfrom]
            record[keyto] = usern
            retrived_objects[value] = usern
    return record

@Configuration(local=True)
class getUserCommand(GeneratingCommand):
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

    user_name = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** user_name of user''',
            require=False)

    daysAgo = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    env = Option(
            doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
            require=False)

    def generate(self):
        # Parse and set arguments
        logger = util.setup_logger(INFO)

        # get config
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        proxy_conf = util.getstanza('getsnow', 'global')
        proxies = util.setproxy(conf, proxy_conf)
        username = conf['user']
        password = conf['password']
        url = conf['url']

        user_query = '%s/api/now/table/%s?sysparm_query=user_name=%s' % (url, 'sys_user', self.user_name)

        response = util.request(user_query,
                                username=username,
                                password=password,
                                headers={'Accept': 'application/json'}
                                )

        if response['code'] == 200:
            records = json.loads(response['msg'])
            # for each event creating dic object for yield
            for record in records['result']:
                record['_time'] = time.mktime(datetime.datetime.strptime(record['sys_created_on'], "%Y-%m-%d %H:%M:%S").timetuple())
                record['url'] = url
                if record['manager']['link']:
                    response = util.request(record['manager']['link'],
                                            username=username,
                                            password=password,
                                            headers={'Accept': 'application/json'}
                                            )
                    manager = json.loads(response['msg'])['result']
                    record['manager'] = manager['name']
                    record['manager_email'] = manager['email']
                    record['manager_phone'] = manager['phone']
                if record['u_office']['link']:
                    response = util.request(record['u_office']['link'],
                                            username=username,
                                            password=password,
                                            headers={'Accept': 'application/json'}
                                            )
                    office = json.loads(response['msg'])['result']
                    record['office_number'] = office['u_office_number']
                if record['location']['link']:
                    response = util.request(record['location']['link'],
                                            username=username,
                                            password=password,
                                            headers={'Accept': 'application/json'}
                                            )
                    location = json.loads(response['msg'])['result']
                    record['office_name'] = location['full_name']
                if record['department']['link']:
                    response = util.request(record['department']['link'],
                                            username=username,
                                            password=password,
                                            headers={'Accept': 'application/json'}
                                            )
                    department = json.loads(response['msg'])['result']
                    record['department'] = department['name']

                # removing unnecessary keys
                record.pop('sys_domain', None)
                record.pop('u_office', None)
                record.pop('company', None)
                record.pop('u_organization_group', None)
                record.pop('u_title', None)
                record.pop('ldap_server', None)
                record.pop('cost_center', None)
                user_sysid = record['sys_id']
                record['sourcetype'] = 'snow:user'
                record['url'] = user_query
                # adding _raw to record
                record['_raw'] = util.tojson(record)
                record['_time'] = time.mktime(datetime.datetime.strptime(record['sys_created_on'], "%Y-%m-%d %H:%M:%S").timetuple())

                #yielding record
                yield record

                # building query string incidents
                time_range = '^opened_at>=javascript:gs.daysAgo(%s)' % self.daysAgo if self.daysAgo else ''
                incident_query = '%s/api/now/table/%s?sysparm_query=opened_by=%s%s' % (url, 'incident', user_sysid, time_range)
                response = util.request(incident_query,
                                        username=username,
                                        password=password,
                                        headers={'Accept': 'application/json'}
                                        )
                incidents = json.loads(response['msg'])['result']
                # replacing all sys_id with user_names
                for incident in incidents:
                    incident = keyreplace(incident, 'closed_by', 'user_name', username, password)
                    incident = keyreplace(incident, 'opened_by', 'user_name', username, password)
                    incident = keyreplace(incident, 'assigned_to', 'user_name', username, password)
                    incident = keyreplace(incident, 'resolved_by', 'user_name', username, password)
                    incident = keyreplace(incident, 'caller_id', 'user_name', username, password)
                    incident = keyreplace(incident, 'u_opened_for', 'user_name', username, password)
                    incident = keyreplace(incident, 'assignment_group', 'name', username, password)
                    incident['url'] = incident_query
                    incident['_raw'] = util.tojson(incident)
                    incident['sourcetype'] = 'snow:incident'
                    incident['_time'] = time.mktime(datetime.datetime.strptime(incident['sys_created_on'], "%Y-%m-%d %H:%M:%S").timetuple())

                    # removing unnecessary keys
                    incident.pop('company', None)
                    incident.pop('location', None)

                    # yield incident record
                    yield incident

                asset_query = '%s/api/now/table/%s?sysparm_query=assigned_to=%s' % (url, 'alm_asset', user_sysid)
                response = util.request(asset_query,
                                        username=username,
                                        password=password,
                                        headers={'Accept': 'application/json'}
                                        )
                assets = json.loads(response['msg'])['result']
                for asset in assets:
                    asset.pop('support_group', None)
                    asset.pop('department', None)
                    asset.pop('model', None)
                    asset.pop('ci', None)
                    asset.pop('company', None)
                    asset.pop('location', None)
                    asset.pop('model_category', None)
                    asset.pop('cost_center', None)
                    asset.pop('sys_domain', None)
                    asset['url'] = asset_query
                    asset['_raw'] = util.tojson(asset)
                    asset['_time'] = time.mktime(datetime.datetime.strptime(asset['sys_created_on'], "%Y-%m-%d %H:%M:%S").timetuple())
                    asset['sourcetype'] = 'snow:asset'
                    yield asset

        else:
            try:
                # If not 200 status_code showing error message in Splunk UI
                record = util.dictexpand(response)
                record['url'] = url
                record['_raw'] = util.tojson(response)
            except Exception as e:
                record = dict()
                record['url'] = url
                record['error'] = e
                record['_raw'] = util.tojson(response)
            yield record

dispatch(getUserCommand, sys.argv, sys.stdin, sys.stdout, __name__)