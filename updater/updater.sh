#!/bin/bash
SOCKET="/tmp/updater.sock"
rm -f "$SOCKET"
echo "Updater sidecar listening on $SOCKET"
while true; do
    socat UNIX-LISTEN:"$SOCKET",fork EXEC:"bash -c '
        echo \"Pulling latest image...\"
        docker compose -f /compose/docker-compose.yml pull morning-briefing
        echo \"Recreating app container...\"
        docker compose -f /compose/docker-compose.yml up -d morning-briefing
        echo \"Pruning old images...\"
        docker image prune -f
        echo \"Update complete\"
    '"
done
