from flask import Flask
import os.path, sys

if sys.platform == "win32":
	from src import manage_db
	from infi.systray import SysTrayIcon
	import webbrowser
	
	global o
	
	def open_browser(systray):
		port = o.get_port(o.config_file)
		if port:
			webbrowser.open_new_tab('http://localhost:' + port)
		else:
			webbrowser.open_new_tab('http://localhost:5656')

	def on_quit_systray(systray):
		o.close_ts(o.ts_db, o.config_file, o.scheduler, o.logger)

	base_dir = '.'
	if getattr(sys, 'frozen', False):
		base_dir = os.path.join(sys._MEIPASS)
		static_folder = os.path.join(base_dir, 'static')
		template_folder = os.path.join(base_dir, 'templates')
		app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
		o = manage_db.ManageDB()
		icon = os.path.join(static_folder, 'images', 'app.ico')
		systray = SysTrayIcon(icon, "TorrentStats", menu_options = (('Open', None, open_browser),), 
							  on_quit=on_quit_systray, default_menu_index=0)
		systray.start()                    
	else:
		app = Flask(__name__)
		o = manage_db.ManageDB()
		icon = os.path.join('src', 'static', 'images', 'app.ico')
		systray = SysTrayIcon(icon, "TorrentStats", menu_options = (('Open', None, open_browser),), 
							  on_quit=on_quit_systray, default_menu_index=0)
		systray.start()

else:
	app = Flask(__name__)

from src import routes