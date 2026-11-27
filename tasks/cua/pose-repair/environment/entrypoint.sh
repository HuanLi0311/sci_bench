#!/bin/bash
set -e
/usr/local/bin/start-desktop > /tmp/desktop.log 2>&1 &
exec "$@"
