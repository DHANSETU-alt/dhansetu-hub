#!/bin/bash
# Build script for Render deployment
# Handles the dashboard subdirectory correctly

set -e

cd dashboard
npm ci
npm run build
