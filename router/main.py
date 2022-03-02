"""
This module listens for messages and triggers reloading of configuration files.
This module is the service side of the implementation.  If you want to
issue reload commands to the service, see the client.py file instead.
"""

import os
import sys

from flask import Flask, jsonify

from .manager import ConfigManager


app = Flask(__name__)

@app.route("/")
def index():
    return jsonify(app.manager.status())

@app.route("/reload", methods=["POST"])
def reload():
    result = app.manager.loadConfig()
    return jsonify(result)

@app.route("/reload/<section>", methods=["POST"])
def reloadOne(section):
    result = app.manager.loadConfig(section)
    return jsonify(result)


def main():
    state_dir = os.environ.get("ROUTER_STATE_DIR", "/tmp/paradrop-router")
    manager = ConfigManager(state_dir, True)
    status = manager.loadConfig()

    app.manager = manager
    app.status = status

    listen_host = os.environ.get("HOST", "localhost")
    listen_port = os.environ.get("PORT", "5001")

    app.run(host=listen_host, port=listen_port)

    manager.unload()


if __name__ == "__main__":
    sys.exit(main())
