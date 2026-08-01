#!/bin/bash
/usr/lib/frr/frrinit.sh start || /usr/lib/frr/docker-start &
sleep 3
exec /usr/sbin/sshd -D -e
