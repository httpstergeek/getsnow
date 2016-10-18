# encoding: utf-8
# Author: Bernardo Macias <bmacias@httpstergeek.com>
#
#
# All rights reserved © 2011-2016 Zillow Group, Inc.
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

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import sys
from helpers import *
from snowpy import *
import json

@Configuration(local=True, type='eventing', retainsevents=True, streaming=False)
class snowIncidentCommand(GeneratingCommand):

    assigned = Option(require=True, validate=validators.List())
    assigned_by = Option(require=False)
    daysAgo = Option(require=False, validate=validators.Integer(0))
    active = Option(require=True, validate=validators.Boolean())
    limit = Option(require=False, validate=validators.Integer(0))
    env = Option(require=False)

    def generate(self):
        self.logger.debug('snowIncidentCommand: %s', self)
        searchinfo = self.metadata.searchinfo
        app = AppConf(searchinfo.splunkd_uri, searchinfo.session_key)
        env = self.env.lower() if self.env else 'production'
        conf = app.get_config('getsnow')[env]
        assigned_by = 'assignment_group' if self.assigned_by == 'group' else 'assigned_to'
        assignment = {'table': 'sys_user_group', 'field': 'name'} if self.assigned_by == 'group' else {'table': 'sys_user', 'field': 'user_name'}
        limit = self.limit if self.limit else 10000
        snowincident = snow(conf['url'], conf['user'], conf['password'])
        sids = snowincident.getsysid(assignment['table'], assignment['field'], self.assigned)
        filters = snowincident.filterbuilder(assigned_by, sids)
        glide = 'sys_created_on>=javascript:gs.daysAgo({})'.format(self.daysAgo) if self.daysAgo else ''
        url = snowincident.reqencode(filters, table='incident', glide_system=glide, active=self.active, sysparm_limit=limit)
        for record in snowincident.getrecords(url):
            record = snowincident.updatevalue(record, sourcetype='snow:incident')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record

dispatch(snowIncidentCommand, sys.argv, sys.stdin, sys.stdout, __name__)