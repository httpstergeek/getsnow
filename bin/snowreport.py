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

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import sys
from helpers import *
from snowpy import *
import json

@Configuration()
class snowReportCommand(GeneratingCommand):

    report = Option(require=True)
    env = Option(require=False)

    def generate(self):
        self.logger.debug('snowReport: %s', self)
        searchinfo = self.metadata.searchinfo
        app = AppConf(searchinfo.splunkd_uri, searchinfo.session_key)
        env = self.env.lower() if self.env else 'production'
        conf = app.get_config('getsnow')[env]
        snowreport = snow(conf['url'], conf['user'], conf['password'])
        url = snowreport.reqencode('rep_title={}'.format(self.report), table='report_home_details')
        for report in snowreport.getrecords(url):
            fields_list = report['rep_field_list'].split(',')
            fields_list.append('sys_created_on')
            url = snowreport.reqencode(report['rep_filter'], table=report['rep_table'], sysparm_fields=fields_list)
            for record in snowreport.getrecords(url):
                record = snowreport.updaterecord(record, sourcetype='snow:report')
                record['_raw'] = json.dumps(record)
                record = dictexpand(record)
                yield record
dispatch(snowReportCommand, sys.argv, sys.stdin, sys.stdout, __name__)