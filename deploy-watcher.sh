#!/bin/bash
# Watches for deploy trigger from GitHub webhook and rebuilds
TRIGGER_FILE="$HOME/TheDailyBrown/data/deploy-trigger.json"
PROJECT_DIR="$HOME/TheDailyBrown"
LOG_FILE="$PROJECT_DIR/data/deploy.log"

echo "Deploy watcher started at $(date)" >> "$LOG_FILE"

while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        echo "$(date) — Deploy triggered: $(cat $TRIGGER_FILE)" >> "$LOG_FILE"
        rm -f "$TRIGGER_FILE"

        cd "$PROJECT_DIR"
        git pull origin 2>&1 >> "$LOG_FILE"
        docker compose pull morning-briefing 2>&1 >> "$LOG_FILE"
        docker compose up -d morning-briefing 2>&1 >> "$LOG_FILE"

        echo "$(date) — Deploy complete" >> "$LOG_FILE"
    fi
    sleep 10
done
