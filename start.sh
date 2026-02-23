#!/bin/bash

# Start the bot in the background (&)
python bot.py &

# Start the Flask app using Gunicorn in the foreground
gunicorn app:app
