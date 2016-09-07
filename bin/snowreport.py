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
from snowpy import snow
from logging import INFO
import json
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option

logger = util.setup_logger(INFO)

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

@Configuration(local=True, type='eventing', retainsevents=True, streaming=False)
class snowReportCommand(GeneratingCommand):
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

    report = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** User to filterby''',
            require=True)

    env = Option(
            doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
            require=False)

    sysparm_fields =Option(
        doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
        require=False)

    def generate(self):
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        #proxy_conf = util.getstanza('getsnow', 'global')
        username = conf['user']
        password = conf['password']
        report = self.report
        sysparm_fields = self.sysparm_fields
        sysparm_fields = '' if sysparm_fields == 'all' else '&sysparm_fields=assigned_to%2Cassignment_group%2Cbusiness_service%2Ccaller_id%2Ccategory%2Cclose_code%2Cclosed_at%2Cclosed_by%2Ccmdb_ci%2Ccontact_type%2Cnumber%2Copened_at%2Copened_by%2Cpriority%2Cresolved_at%2Cresolved_by%2Cseverity%2Cshort_description%2Cstate%2Csubcategory%2Cu_incident_duration%2Csys_created_on%2Cshort_description'
        url = conf['url']
        snowtask = snow(url, username, password)
        filter = 'rep_title={}'.format(report)
        url = snowtask.reqencode([filter], table='report_home_details')
        for record in snowtask.getrecords(url):
            report_filter = record['rep_filter']
            url = snowtask.reqencode([report_filter], table='incident')
            for record in snowtask.getrecords(url + sysparm_fields):
                record['_raw'] = json.dumps(record)
                record = snowtask.updatetime(record, 'sys_created_on', '_time')
                record = dictexpand(record)
                yield record

dispatch(snowReportCommand, sys.argv, sys.stdin, sys.stdout, __name__)