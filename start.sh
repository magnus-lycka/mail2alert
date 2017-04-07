#!/usr/bin/env bash

#docker network create mail2alert

docker run \
    -d \
    --name mail2alert-redis \
    --restart=always \
    --publish 6379:6379 \
    --volume /storage/mail2alert/redis:/var/lib/redis \
    sameersbn/redis:latest

docker run \
    -d \
    --name mail2alert-app \
    --restart=always \
    --publish 1025:1025 \
    --publish 50101:50101 \
    mail2alert

#    --net mail2alert \
#    --net mail2alert \
