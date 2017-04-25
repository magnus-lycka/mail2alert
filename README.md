# mail2alert
_Send alerts based on received email._

[![Build Status](https://travis-ci.org/magnus-lycka/mail2alert.svg?branch=master)](https://travis-ci.org/magnus-lycka/mail2alert)


This tool is intended to help distribute emails to
different addresses based on their contents.

The primary goal is to distribute GoCD alerts to
group email addresses based on their subject lines.


## Requirements

This software is written using Pythons asyncio libraries,
and the new async / await syntax. It's been developed and
tested with Python 3.6.1.

The easiest way to deploy it is probably in a docker, see
__Deploy and Run__ section below.


## Operation

The core process is an SMTP server.

For each received email, the server will consult all its
managers. (It's just the mail & gocd managers for now.)
The first manager who wants the email will get it, so
criteria for accepting emails should not overlap. For
now, the critera is a match on either from address or
to address.

Emails which aren't wanted by any manager will be passed
on to another SMTP server.

If a manager wants a message, it's given the recipient
list, the from address and the message body. It can then
return the same triplet modified as it sees fit. The
typical change is to replace the recipient with one determined
from settings and rules in the manager.


## Configuration

The configuration is in a file called `configuration.yml`
located in the directory where the server is started.
It could look like this.

    ---
    local-smtp: localhost:1025
    remote-smtp: localhost:8025
    managers:
      - name: gocd
        url: http://localhost:8080/go
        user: olle
        passwd: pelle
        messages-we-want:
          to: mail2alert@example.com
        rules:
          - actions:
              - mailto:cat@example.com
            filter:
              events:
                - BREAKS
              function: pipelines.in_group
              args:
                - my-group
          - actions:
              - mailto:cat@example.com
            filter:
              events:
                - BREAKS
                - FIXED
              function: pipelines.name_like_in_group
              args:
                - (.+)-release.*
                - my-group
      - name: mail
        messages-we-want:
          from: go@example.com
        rules:
          - actions:
              - mailto:sys@example.com
              - mailto:op@example.com
            filter:
              function: mail.in_subject
              args:
                - server
                - backup

In this case, the ordering of managers is deliberate.
The `messages-we-want` clause of `mail` means that the
`mail` manager would have eaten the messages intended
for the `gocd` manager.

`local-smtp` defines the hostname:port for the builtin
SMTP server in _mail2alert_ to listen to.

`remote-smtp` defines the hostname:port which _mail2alert_
should send emails to.

`managers` is a list of mail2alert managers. Each list
item describes the settings for than manager. Some fields
are manager specific, but the following are generic:

`name` must match the name of the Python module defining
the manager.

`messages-we-want` contains either the key `to` followed by
a recipient address we match on, or the key `from` followed
by a sender address we match on.

`rules` is a section containing a list of rules which the
manager uses to determine what to do with each email it wanted.
The following fields for a rule are common for managers:

`actions` is a list of URIs representing what to do with the
message. `mailto` URIs mean that the process_message method
should return the email address in the recipient list. Other
URIs are so-far not supported, but Slack might be next in turn.

`filter` is a manager specific field used by the rules to
determine whether we want this message.


## Managers

Each manager is a module containing a which implements this
interface

    class Manager:
        def __init__(self, conf):
            """
            Get's the part of the configuration specific to
            this manager.
            """

        def wants_message(self, mail_from, rcpt_tos, binary_content):
            return boolean  # True==we want this email

        def process_message(self, mail_from, rcpt_tos, binary_content):
            """
            Use the rules to determine whether we want the message,
            and how to modify any of the arguments before returning
            it. Make recipients an empty list if you don't want to
            send any email.
            """
            return mail_from, recipients, binary_content

Mail2alert will replace the `From:` and `To:` fields in the email
content with the values returned before sending it.


## The mail manager

The mail manager is for rules which can be determined without
consulting anything beyond the email content.

It has the following rule function:
 - mail.in_subject
   - Will match a message if all words given as arguments are
     found in the subject line. (Case insensitive.)

The `filter` part of each rule can contain the following fields:

`function` the rule function listed above.

`args` needed for `function` as indicated above.


## The gocd manager

The gocd manager reads the pipeline group configuration periodically,
to determine which pipelines there are, and what pipeline groups
they belong to. For this to work, we need three settings in the
manager section of the configuration:

`url:` e.g. `https://localhost:8154/go`

`user:` e.g. `$GOUSER`

`passwd:` e.g. `$GOPASS`

Providing the GoCD authentification as environment variables means that
you can place the configuration file under configuration control without
putting security sensitive information in it.

The gocd manager extracts the `subject` from each email, and
from job progress emails, it will extract the `pipeline` name
and `event` from the subject.

It has the following rule functions:
 - pipelines.all
   - all pipelines will match.
 - pipelines.in_group
   - Takes a group name as argument. Will match if name of
     pipeline in message matches is in the pipeline group
     provided as argument.
 - pipelines.name_like_in_group
   - takes two arguments:
     - a regular expression pattern
     - a group name
   - a message will be selected if its pipeline is like
     a pipeline in the provided group when the regular expression
     has been applied. E.g. given arguments `(.+)-release.*`
     and `mygroup`, it will match if message contained pipeline
     `ppp-release-1.2.3` and a pipline named `ppp` is in `mygroup`.

The `filter` part of each rule can contain the following fields:

`event` a subset of values listed below. If provided in the rule,
messages will only be selected if any of the events listed has
ben identified in the message subject line.
  - PASSES
  - FAILS
  - BREAKS
  - FIXED
  - CANCELLED

`function` one of the rule functions listed above.

`args` needed for `function` as indicated above.

### GoCD server settings

There are two settings which are needed in the GoCD server:
  - In Admin => Server Configuration=> Email Notification,
    configure hostname and port to send emails to mail2alert,
    i.e. matching `local-smtp` in the _mail2alert_ config.

  - For some user, in Preferences => Notifications set email
    to a value which `messages-we-want: to:`
  - Set one filter for the user to `[Any Pipeline] [Any Stage] All All`
    - To Be Investigated: Does this user need read permissions on all
      pipelines groups?


## Deploy and Run

The `build.sh` script builds a new docker image from the `Dockerfile`

The `run.sh` script runs the docker image. Note that it's set to
run the docker image in the insecure `--network=host` mode, which
is considered insecure. One argument is needed, to provide the
path to the directory where the valid `configuration.yml` is located.
This directory will be read-only-mounted by the docker.

`nc localhost 50101` provides you with an interactive
monitor to the application for debugging. See
http://aiomonitor.readthedocs.io/en/latest/

Use `docker restart mail2alert-app` after changing
`configuration.yml` to reread it.
