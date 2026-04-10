#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Installation de Chrome pour Pyppeteer
apt-get update && apt-get install -y wget gnupg
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/local/sources.list.d/google.list'
apt-get update && apt-get install -y google-chrome-stable