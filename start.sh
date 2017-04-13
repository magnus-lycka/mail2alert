#!/usr/bin/env bash

docker run \
    -d \
    --name mail2alert-redis \
    --net=host \
    --restart=always \
    --publish 6379:6379 \
    --volume /storage/mail2alert/redis:/var/lib/redis \
    sameersbn/redis:latest

docker run \
    -d \
    --name mail2alert-app \
    --net=host \
    --restart=always \
    --publish 1025:1025 \
    --publish 50101:50101 \
    --publish 50102:50102 \
    mail2alert
