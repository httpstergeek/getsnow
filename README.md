Copyright (C) 2006-2015 Zillow Group, Inc. All Rights Reserved.

Get Service Now - A Splunk Search Command for Service Now
=================

Getsnow is a Splunk Search command that uses the snow (sevicenow) api to retrieves raw json data. This app differs from
the Splunk Add-on for Service Now by allowing users to query any table, prebuilt or custom, by using filters.  A filter is
any top level key in the json event such as active, assigned_to, category, etc. Additionally this support multiple
service now environments.  Multiple environments may include poc, dev, or prod can access by creating additional stanza
and adding the argument 'env=<environment>'.

This command additional allows the user to request data from any service now table by addi
ng 'table=<string>' to there
query. The default is set to incidence table.

click here for [Service Now Table API documentation]

[Service Now Table API documentation]:http://wiki.servicenow.com/index.php?title=Table_API

##Supports:
* Supports multiple Service Now Instances
* Proxy support




Requirements
---------

* This version has been test on 6.x and should work on 5.x.

* App is known to work on Linux,and Mac OS X, but has not been tested on other operating systems. Window should work

* App requires network access to Service Now instance

* Minimum of 2 GB RAM and 1.8 GHz CPU.



Prerequisites
---------
* Service Now EUREKA or Higher

* Splunk version 6.x or Higher

You can download it [Splunk][splunk-download].  And see the [Splunk documentation][] for instructions on installing and more.
[Splunk]:http://www.splunk.com
[Splunk documentation]:http://docs.splunk.com/Documentation/Splunk/latest/User
[splunk-download]:http://www.splunk.com/download


Installation instructions
---------

1) copy repo into $SPLUNK_HOME/etc/apps/.

2) create $SPLUNK_HOME/etc/apps/getsnow/local/getsnow.conf.

3) configure [production] stanza with url to Service Now instance. Note: if proxy look at README for proxy config.


Note:   The Service Now user that is defined in each stanza requires read permission to incidents table at minimum.
        If you plan on using the table argument you must also grant the user read permission to those tables.
        consult with our ServiceNow Admin.

Viewing Available Tables
--------

1) Login to service now.

2) Browse *System Definition* Tab

3) Click Tables & Columns

4) Find the table of interest under the Tables Names section.
   Note: items within brackets are the real name of the table.



Example Command
---------

| getsnow filters="active=true contact_type=phone" daysAgo=30

    OR

| getsnow filters="active=true contact_type=phone" glideSystem="beginningOfLastWeek()"

    OR

| getsnow filters="active=true contact_type=phone" glideSystem="beginningOfLastWeek()" env=dev
    Note: The value dev for env should match an stanza defined within getsnow.conf:wq

Recommendations
---------

It is recommend that this be installed on an Search head.
