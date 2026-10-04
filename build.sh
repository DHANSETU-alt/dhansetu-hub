#!/bin/bash
# Build script for Render deployment
# Handles the dashboard subdirectory correctly

set -e

cd dashboard
npm install
npm run build
