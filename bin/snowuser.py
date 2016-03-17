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
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option


logger = util.setup_logger(INFO)

@Configuration(local=True)
class snowUserCommand(GeneratingCommand):
    """ %(synopsis)

    ##Syntax
    .. code-block::
    snowuser env=<str> user_name=<str> daysAgo=<int> env=<str>

    ##Description

    Returns json events for Service Now API from tables.  Limit 1000 events.

    ##Example

    Return json events where where active is true and contact_type is phone for the past 30 days.

    .. code-block::
        | snowuser user_name=rick daysAgo=30
        OR
        | snowuser env=production user_name=mortey
        OR
        | snowuser env=production user_name="mortey,rick"

    """

    user_name = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** user_name of user''',
            require=True)

    daysAgo = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    env = Option(
            doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
            require=False)

    def generate(self):
        logger = util.setup_logger(INFO)
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        # Proxy not currently used in this version
        # proxy_conf = util.getstanza('getsnow', 'global')
        # proxies = util.setproxy(conf, proxy_conf)
        username = conf['user']
        password = conf['password']
        url = conf['url']
        value_replacements = conf['value_replacements']
        user_name = self.user_name.split(',')
        daysAgo = int(self.daysAgo) if self.daysAgo else 30
        snowuser = snow(url, username, password)
        snowuser.replacementsdict(value_replacements)
        user_info = snowuser.getsysid('sys_user', 'user_name', user_name, mapto='user_name')
        for record in user_info[1]:
            record = snowuser.updaterecord(record, sourcetype='snow:user')
            record['_raw'] = util.tojson(record)
            yield record
        exuded = snowuser.filterbuilder('assigned_to', user_info[0])
        url = snowuser.reqencode([exuded], table='alm_asset')
        for record in snowuser.getrecords(url):
            record = snowuser.updaterecord(record, sourcetype='snow:asset')
            record['_raw'] = util.tojson(record)
            yield record
        exuded = snowuser.filterbuilder('opened_by', user_info[0])
        url = snowuser.reqencode([exuded], days=daysAgo)
        for record in snowuser.getrecords(url):
            record = snowuser.updaterecord(record, sourcetype='snow:incident')
            record['_raw'] = util.tojson(record)
            yield record

dispatch(snowUserCommand, sys.argv, sys.stdin, sys.stdout, __name__)