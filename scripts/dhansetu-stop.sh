#!/bin/zsh
set -u
uid="$(id -u)"
for label in in.dhansetu.paperclip in.dhansetu.web in.dhansetu.api; do
  if launchctl print "gui/$uid/$label" >/dev/null 2>&1; then
    launchctl bootout "gui/$uid/$label" || true
    echo "stopped $label"
  else
    echo "$label not loaded"
  fi
done
