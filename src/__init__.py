from flask import Flask
import os.path, sys

if sys.platform == "win32":
	base_dir = '.'
	if getattr(sys, 'frozen', False):
		base_dir = os.path.join(sys._MEIPASS)
		static_folder = os.path.join(base_dir, 'static')
		template_folder = os.path.join(base_dir, 'templates')
		app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)           
	else:
		app = Flask(__name__)
else:
	app = Flask(__name__)

from src import routes