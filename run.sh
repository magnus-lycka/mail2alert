#!/usr/bin/env bash

docker run \
    -d \
    --name mail2alert-app \
    --net=host \
    --restart=always \
    --publish 1025:1025 \
    --publish 50101:50101 \
    --publish 50102:50102 \
    --volume $1:/mail2alert_config:ro \
    -e "MAIL2ALERT_CONFIGURATION=/mail2alert_config/configuration.yml" \
    mail2alert
