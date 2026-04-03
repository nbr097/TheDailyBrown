#!/bin/bash
case "$1" in
    reset-webauthn)
        sqlite3 data/morning.db "DELETE FROM webauthn_credentials;"
        echo "WebAuthn credentials cleared. Re-register on next dashboard visit."
        ;;
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
        echo "Usage: ./manage.sh {reset-webauthn|logs|restart|status}"
        ;;
esac
