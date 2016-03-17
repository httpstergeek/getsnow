# This file contains possible attributes and values you can use to configure getsnow,
# sets connections string, user, name which is distributed to search heads.
#
# This is an getsnow.conf in $SPLUNK_HOME/etc/getsnow/default.  To set custom configurations,
# place an getsnow.conf $SPLUNK_HOME/etc/getsnow/local.

# GLOBAL SETTINGS
# Use the [global] stanza to define any global settings
#   * You can also define global settings outside of any stanza, at the top of the file.
#   * Each conf file should  have at most one global stanza, at the top of the file.
#   * If an attribute is define at both the global level and in a specific stanza, the
#     value in the specific stanza takes precedence.


[global]
proxy_url = <url>:<port>|<url>
* set proxy server,  optional.
* EXAMPLE:  proxy.foo.com:8080 or proxy.foo.com

proxy_user = <string>
* set proxy user, optional.

proxy_password = <string>
* set proxy user password, optional.

#*******
# GENERAL SETTINGS:
# This following attribute/value pairs are valid for all stanzas.  The [production] stanza
# is required. Additional stanzas can be define which can be used by user by specifying instance=<string>.
# This is if your environment has multiple Graphite instances
#*******


[<env>]
url = http(s)://fqdn
* sets url for service snow instance.
* EXAMPLE: http://mycompany.service-now

user = Service Now User
* sets user for Service Snow instance, optional.

password = Service Now user password
* set password for Service Now user, optional.  Must define user.

value_replacements = Keys to replace from link record where sys_id is present
* Sets release to Service Now release code.  Defaults to Eureka. Fuji
* EXAMPLE: closed_by=user_name,opened_by=user_name,assigned_to=user_name,resolved_by=user_name,caller_id=user_name,u_opened_for=user_name,assignment_group=name,request=number,parent=number,request_item=number
* In the example closed_by is the key in the Service Now record where a sys_id and link are the value.  user_name is the key in the link used to replaced the update the original record.
