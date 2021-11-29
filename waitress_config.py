from waitress import serve
from src import app
import os.path, sys
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(sys.executable), "TorrentStats", "config.ini"))
port = config['Preferences']['port']
serve(app, host='0.0.0.0', port=port, threads=6, _quiet=True)