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


from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import sys
from helpers import *
from snowpy import *
import json

@Configuration()
class snowTaskCommand(GeneratingCommand):

    assigned = Option(require=True, validate=validators.List())
    assigned_by = Option(require=False)
    daysAgo = Option(require=False, validate=validators.Integer(0))
    active = Option(require=True, validate=validators.Boolean())
    limit = Option(require=False, validate=validators.Integer(0))
    env = Option(require=False)

    def generate(self):
        searchinfo = self.metadata.searchinfo
        app = AppConf(searchinfo.splunkd_uri, searchinfo.session_key)
        env = self.env.lower() if self.env else 'production'
        conf = app.get_config('getsnow')[env]
        assigned_by = 'assignment_group' if self.assigned_by == 'group' else 'assigned_to'
        assignment = {'table': 'sys_user_group', 'field': 'name'} if self.assigned_by == 'group' else {'table': 'sys_user', 'field': 'user_name'}
        limit = self.limit if self.limit else 10000
        snowtask = snow(conf['url'], conf['user'], conf['password'])
        sids = snowtask.getsysid(assignment['table'], assignment['field'], self.assigned)
        filters = snowtask.filterbuilder(assigned_by, sids)
        glide = 'sys_created_on>=javascript:gs.daysAgo({})'.format(self.daysAgo) if self.daysAgo else ''
        url = snowtask.reqencode(filters, table='sc_task', glide_system=glide, active=self.active, sysparm_limit=limit)
        for record in snowtask.getrecords(url):
            record = snowtask.updaterecord(record, sourcetype='snow:task')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record

dispatch(snowTaskCommand, sys.argv, sys.stdin, sys.stdout, __name__)