#!/bin/bash


REPO=harbor.anthonyuk.dev/library

set -e

VERSION="dev-$(date -u '+%Y%m%dT%H%M')"
TAG="$VERSION"

echo "##### Build version: $VERSION #####"

docker build --build-arg=VERSION="$VERSION" -t $REPO/truenas-cert-sync:$TAG .

docker tag $REPO/truenas-cert-sync:$TAG $REPO/truenas-cert-sync:latest

docker push -a $REPO/truenas-cert-sync
