#!/bin/bash
cd /home/vm/dev/radiator
source venv/bin/activate
exec python -m radiator.telegram_bot.main
