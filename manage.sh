#!/bin/bash
case "$1" in
    logs)
        docker compose logs -f morning-briefing
        ;;
    restart)
        docker compose restart morning-briefing
        ;;
    status)
        curl -s http://localhost:8000/health | python3 -m json.tool
        ;;
    *)
        echo "Usage: ./manage.sh {logs|restart|status}"
        ;;
esac
