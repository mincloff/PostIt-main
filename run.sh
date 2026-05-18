#!/bin/bash
# Quick launcher for Django ASGI app with mkcert certs

APP="postit.asgi:application"
HOST="0.0.0.0"
PORT=8000
KEYFILE="/home/mehar/Desktop/postit-final/socialhub/postit/meharumar.root+2-key.pem"
CERTFILE="/home/mehar/Desktop/postit-final/socialhub/postit/meharumar.root+2.pem"

uvicorn "$APP" \
  --host "$HOST" \
  --port "$PORT" \
  --ssl-keyfile "$KEYFILE" \
  --ssl-certfile "$CERTFILE" \
  --reload
