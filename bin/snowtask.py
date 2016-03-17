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

    user_name = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** user_name of user''',
            require=False)
    assignment_group = Option(
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
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        #proxy_conf = util.getstanza('getsnow', 'global')
        username = conf['user']
        password = conf['password']
        active = self.active.strip() if self.active else 'True'
        user_name = self.user_name.split(',') if self.user_name else []
        assigment_group = self.assignment_group.split(',') if self.assignment_group else []
        daysAgo = int(self.daysAgo) if self.daysAgo else None
        limit = self.limit
        url = conf['url']
        value_replacements = conf['value_replacements']
        if active:
            try:
                active = active[0].upper() + active[1:].lower()
                active = ast.literal_eval(active)
            except:
                active = True
        if limit:
            try:
                limit = int(limit)
            except:
                limit = 10000
        snowtask = snow(url, username, password)
        snowtask.replacementsdict(value_replacements)
        user_info = snowtask.getsysid('sys_user', 'user_name', user_name, mapto='user_name')[0]
        group_info = snowtask.getsysid('sys_user_group', 'name', assigment_group, mapto='name')[0]
        exuded1 = snowtask.filterbuilder('assigned_to', user_info)
        exuded2 = snowtask.filterbuilder('assignment_group', group_info)
        url = snowtask.reqencode([exuded1, exuded2], table='sc_task', active=active, days=daysAgo)

        for record in snowtask.getrecords(url,limit=limit):
            record = snowtask.updaterecord(record, sourcetype='snow:task')
            record['_raw'] = util.tojson(record)
            yield record

dispatch(snowTaskCommand, sys.argv, sys.stdin, sys.stdout, __name__)