#!/bin/bash

# replace with actual paths and names
PROJECT_DIR= ???
AUTH_KEY= ???

cd "$PROJECT_DIR"|| exit

echo "Authenticating with Google Artifact Registry..."
cat "./$AUTH_KEY" | docker login -u _json_key --password-stdin https://us-east4-docker.pkg.dev

echo "Checking for new images..."
docker-compose pull

echo "Applying updates..."
docker-compose up -d

echo "Cleaning up..."
docker image prune -f

echo "Update complete."
