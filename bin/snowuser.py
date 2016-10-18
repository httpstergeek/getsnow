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

@Configuration(local=True, type='eventing', retainsevents=True, streaming=False)
class snowUserCommand(GeneratingCommand):

    user_name = Option(require=True, validate=validators.List())
    daysAgo = Option(require=False, validate=validators.Integer(0))
    env = Option(require=False)

    def generate(self):
        self.logger.debug('snowuser: %s', self)
        searchinfo = self.metadata.searchinfo
        app = AppConf(searchinfo.splunkd_uri, searchinfo.session_key)
        env = self.env.lower() if self.env else 'production'
        conf = app.get_config('getsnow')[env]
        snowuser = snow(conf['url'], conf['user'], conf['password'])
        filters = snowuser.filterbuilder('user_name', self.user_name)
        query_string = snowuser.reqencode(filters, 'sys_user')
        user_sid = []
        for record in snowuser.getrecords(query_string):
            user_sid.append(record['sys_id'])
            record = snowuser.updatevalue(record, sourcetype='snow:user')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record
        filters = snowuser.filterbuilder('assigned_to', user_sid)
        url = snowuser.reqencode(filters, table='alm_asset')
        for record in snowuser.getrecords(url):
            record = snowuser.updatevalue(record, sourcetype='snow:asset')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record
        filters = snowuser.filterbuilder('opened_by', user_sid)
        glide = 'sys_created_on>=javascript:gs.daysAgo({})'.format(self.daysAgo) if self.daysAgo else ''
        url = snowuser.reqencode(filters, table='incident', glide_system=glide)
        for record in snowuser.getrecords(url):
            record = snowuser.updatevalue(record, sourcetype='snow:incident')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record

dispatch(snowUserCommand, sys.argv, sys.stdin, sys.stdout, __name__)