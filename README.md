Copyright (C) 2006-2015 Zillow Group, Inc. All Rights Reserved.

Get Service Now - A Splunk Search Command for Service Now
=================

Get Service now is a Splunk Search command that uses the snow api  and retrieves raw json data.
This Splunk utilizes requests python modules.

##Supports:
* Supports multiple Service Now Instances

* Proxy support




Requirements
---------

* This version has been test on 6.x and should work on 5.x.

* App is known to work on Linux,and Mac OS X, but has not been tested on other operating systems. Window should work

* App requires network access to Service Now instance

* Miminum of 2 GB RAM and 1.8 GHz CPU.



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

3) configure [production] stanza with url to graphite instance. Note: if proxy look at README for proxy config.

Example Command
---------

`| getsnow filters="active=true contact_type=phone" daysAgo=30
    OR
`| getsnow filters="active=true contact_type=phone" glideSystem="beginningOfLastWeek()"
    OR
`| getsnow filters="active=true contact_type=phone" glideSystem="beginningOfLastWeek()" env=dev

Recommendations
---------

It is recommend that this be installed on an Search head.
