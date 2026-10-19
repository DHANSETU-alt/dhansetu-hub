#!/bin/bash
# Cron setup for daily research and content publishing jobs (Tasks #8+10)
#
# This script sets up the daily cron jobs for:
# 1. research_daily.py - 08:00 IST daily (fetches news, generates insights)
# 2. publish_content.py - 08:30 IST daily (publishes insights to platforms)
#
# Usage: bash orchestrator/jobs/cron_setup.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Time zone: India Standard Time (IST) is UTC+5:30
# 08:00 IST = 02:30 UTC
# 08:30 IST = 03:00 UTC

echo "Setting up cron jobs for Shakthi Research Automation..."
echo "Project root: $PROJECT_ROOT"

# Create crontab entry for research job
RESEARCH_JOB="30 2 * * * cd $PROJECT_ROOT && python -c \"from orchestrator.jobs import research_daily; research_daily.InsightGenerator().run()\" >> logs/research_cron.log 2>&1"

# Create crontab entry for publishing job
PUBLISH_JOB="0 3 * * * cd $PROJECT_ROOT && python -c \"from orchestrator.jobs import publish_content; publish_content.ContentPublisher().run()\" >> logs/research_cron.log 2>&1"

echo ""
echo "Add the following lines to your crontab (crontab -e):"
echo ""
echo "# Research automation job - Daily at 08:00 IST (02:30 UTC)"
echo "$RESEARCH_JOB"
echo ""
echo "# Content publishing job - Daily at 08:30 IST (03:00 UTC)"
echo "$PUBLISH_JOB"
echo ""
echo "Or run this command to add them automatically:"
echo "crontab -l | { cat; echo '# Research automation'; echo '$RESEARCH_JOB'; echo '# Content publishing'; echo '$PUBLISH_JOB'; } | crontab -"
echo ""
