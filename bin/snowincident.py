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
import time
import json
import requests

@Configuration()
class snowIncidentCommand(GeneratingCommand):

    assigned = Option(require=True, validate=validators.List())
    assigned_by = Option(require=False)
    daysAgo = Option(require=False, validate=validators.Integer(0))
    daysBy = Option(require=False)
    active = Option(require=True, validate=validators.Boolean())
    limit = Option(require=False, validate=validators.Integer(0))
    env = Option(require=False)

    def generate(self):
        self.logger.debug('snowIncidentCommand: %s', self)
        searchinfo = self.metadata.searchinfo
        app = AppConf(searchinfo.splunkd_uri, searchinfo.session_key)
        env = self.env.lower() if self.env else 'production'
        conf = app.get_config('getsnow')[env]
        username = conf['user']
        password = conf['password']
        url = conf['url']
        assigned_by = 'assignment_group' if self.assigned_by == 'group' else 'assigned_to'
        assignment = {'table': 'sys_user_group', 'field': 'name'} if self.assigned_by == 'group' else {'table': 'sys_user', 'field': 'user_name'}
        daysAgo = int(self.daysAgo) if self.daysAgo else None
        limit = self.limit if self.limit else 10000
        snowincident = snow(url, username, password)
        sids = snowincident.getsysid(assignment['table'], assignment['field'], self.assigned)
        filters = snowincident.filterbuilder(assigned_by, sids)
        glide = 'sys_created_on>=javascript:gs.daysAgo({})'.format(self.daysAgo)
        url = snowincident.reqencode([filters], table='incident', glide_system=glide, active=self.active, sysparm_limit=limit)
        for record in snowincident.getrecords(url):
            record = snowincident.updatevalue(record, sourcetype='snow:incident')
            record['_raw'] = json.dumps(record)
            record = dictexpand(record)
            yield record


dispatch(snowIncidentCommand, sys.argv, sys.stdin, sys.stdout, __name__)
"""
import util
import sys
import ast
from snowpy import snow
from logging import INFO
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option


logger = util.setup_logger(INFO)


@Configuration(local=True, type='eventing', retainsevents=True, streaming=False)
class snowIncidentCommand(GeneratingCommand):
    "" " %(synopsis)

    ##Syntax
    .. code-block::
    ggetuseretuser env=<str> user_name=<str> daysAgo=<int> env=<str>

    ##Description

    Returns json events for Service Now API from tables.  Limit 1000 events.

    ##Example

    Return json events where where active is true and contact_type is phone for the past 30 days.

    .. code-block::
        | getsnow user_name=rick daysAgo=30
        OR
        | getsnow env=production user_name=mortey

    "" "

    user_name = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** User to filterby''',
            require=False)

    assignment_group = Option(
            doc='''**Syntax:** **assignment_group=***<str>*
        **Description:** Assignment group in Service Now''',
            require=False)

    filterBy = Option(
            doc='''**Syntax:** **filterBy=***<str>*
        **Description:** field to filter by . Default is assigned_to''',
            require=False)

    daysAgo = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** How many days ago to retrieve incidents''',
            require=False)

    daysBy = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** Service Now field to retrieve records using dayAgo''',
            require=False)

    active = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** Boolean True/False.  If record is active. Default None which will pull both''',
            require=False)

    limit = Option(
            doc='''**Syntax:** **table=***<str>*
        **Description:** Maximium number of records in batches of 10,000''',
            require=False)

    env = Option(
            doc='''**Syntax:** **env=***<str>*
        **Description:** Environment to query. Environment must be in conf. Default production.''',
            require=False)

    def generate(self):
        logger = util.setup_logger(INFO)
        env = self.env.lower() if self.env else 'production'
        conf = util.getstanza('getsnow', env)
        #proxy_conf = util.getstanza('getsnow', 'global')
        username = conf['user']
        password = conf['password']
        active = self.active
        user_name = self.user_name.split(',') if self.user_name else []
        assigment_group = self.assignment_group.split(',') if self.assignment_group else []
        daysAgo = int(self.daysAgo) if self.daysAgo else None
        limit = self.limit
        daysBy = self.daysBy if self.daysBy else 'opened_at'
        filterBy = self.filterBy if self.filterBy else 'assigned_to'
        url = conf['url']
        value_replacements = conf['value_replacements']
        if active:
            try:
                active = active.strip()
                active = active[0].upper() + active[1:].lower()
                active = ast.literal_eval(active)
            except:
                active = True
        if limit:
            try:
                limit = int(limit)
            except:
                limit = 10000
        snowincident = snow(url, username, password)
        snowincident.replacementsdict(value_replacements)
        user_info = snowincident.getsysid('sys_user', 'user_name', user_name, mapto='user_name')[0]
        group_info = snowincident.getsysid('sys_user_group', 'name', assigment_group, mapto='name')[0]
        exuded1 = snowincident.filterbuilder(filterBy, user_info)
        exuded2 = snowincident.filterbuilder('assignment_group', group_info)
        url = snowincident.reqencode([exuded1, exuded2], table='incident', active=active, timeby=daysBy, days=daysAgo)
        for record in snowincident.getrecords(url, limit=limit):
            # record = snowincident.updaterecord(record, sourcetype='snow:incident',lookup=False)
            record = snowincident.updatevalue(record, sourcetype='snow:incident')
            record['_raw'] = util.tojson(record)
            yield record

dispatch(snowIncidentCommand, sys.argv, sys.stdin, sys.stdout, __name__)
"""