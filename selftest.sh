#!/usr/bin/env bash

docker run \
    --rm \
    --net=host \
    --volume $1:/mail2alert_config:ro \
    -e "MAIL2ALERT_CONFIGURATION=/mail2alert_config/configuration.yml" \
    mail2alert --test
