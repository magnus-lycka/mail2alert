# mail2alert
_Send alerts based on received email._

This tool is intended to help distribute emails to
different addresses based on their contents.

The primary goal is to distribute GoCD alerts to
group email addresses based on their subject lines.

The secondary goal is to build this functionality
from loosely coupled, simple and if reasonable, fairly
generic tools.

## Operation

The core process is a small SMTP server. Action for received
emails can be one of:
  - send
  - process

The action can (as it looks right now) be determined from
the recipient address.

The SMTP server will have an external SMTP server defined.
If action is `send`, the email is simply relayed to that
server.

If the action is `process`, configuration settings determine
what to do next. The initial intention is to use the subject
line of the email to determine 1) whether to forward this
email, 2) which address to sent it to.

Future extensions might include sending the alert to e.g.
a web service instead of an email address.

## GoCD settings

Our idea is that GoCD pipeline configurations can have a
parameter whose name starts with `MAIL2ALERT_`. For instance
`MAIL2ALERT_BREAKS` or `MAIL2ALERT_FIXED_1`. The part after
the first underscore is one of:

  - ALL
  - PASSES
  - FAILS
  - BREAKS
  - FIXED
  - CANCELLED
  - NODEFAULT

The value `NODEFAULT` is intended to prevent the default
behaviour defined below, the other values are explained 
in the GoCD documentation, here:
https://docs.gocd.io/current/faq/notifications_page.html

Pipeline parameters are explained here:
https://docs.gocd.io/current/configuration/admin_use_parameters_in_configuration.html

After this, there might be an optional underscore with an
arbitrary suffix. The reason for this is to allow more than
one action to be executed on the same event for the same pipeline.

The value for a parameter is a mailto-URL, without additional headers.
See: https://tools.ietf.org/html/rfc2368

Using other values than mailto-URLs would be a way to extend functionality
in the future.

## Supporting functions

Since the initial usecase concerns getting sane alerts to
group emails for GoCD events, we need some support functions.

### mail2alert-gocd-pipelines

This supporting function will periodically scan the GoCD server pipeline 
settings using the pipeline configuration REST API, ( see
https://api.gocd.io/current/#pipeline-groups and
https://api.gocd.io/current/#get-pipeline-config )
to find the relevant MAIL2ALERT parameters and update the configuration
of the system based on them.

### mail2alert-gocd-pipelinegroups

This support function will periodically scan the GOCD configuration
as described above, and add a default `MAIL2ALERT` paramameter for
all pipelines which have no such parameter. The default is determined
from a configuration setting for each pipeline group.

## Configuration structure

Configuration for mail2alert might look something along these lines:

 - mail2alert
   - listen-smtp
   - remote-smtp
   - gocd
     - url
     - user
     - password
     - filter
     - pipelinegroups
        - name
           - event: action
     - pipelines
        - filter
        - name
           - event
             - action

The tricky part is that the `pipelines` part will get updated on the fly...
