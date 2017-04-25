#!/usr/bin/env bash
set -ex
USERNAME=thinkware
IMAGE=mail2alert

version=`cat VERSION`
echo "version: $version"
docker build -t $USERNAME/$IMAGE:latest .
docker tag $USERNAME/$IMAGE:latest $USERNAME/$IMAGE:$version
docker push $USERNAME/$IMAGE:latest
docker push $USERNAME/$IMAGE:$version
