#!/bin/sh
# Hosting platforms mount the data volume owned by root, and not all of them let you pick the
# container user. Start as root, hand /data to the app user, then drop root for good.
set -e
if [ "$(id -u)" = 0 ]; then
    if [ -d /data ] && [ "$(stat -c %u /data)" != 10001 ]; then
        chown -R 10001:10001 /data
    fi
    exec setpriv --reuid=10001 --regid=10001 --init-groups -- "$@"
fi
exec "$@"
