from flask import Flask, render_template, jsonify, request
from operator import itemgetter
from src import app
from src import client_connect, manage_db
import sqlite3
import locale
import configparser
import os, os.path, sys
import signal
from datetime import datetime, time, timedelta

global o
o = manage_db.ManageDB()

def sig_handler(signum, frame):
	o.close_ts(o.ts_db, o.config_file, o.scheduler, o.logger)

signal.signal(signal.SIGTERM, sig_handler)

if sys.platform == "win32":
	from src import win_functions
	from infi.systray import SysTrayIcon
	import webbrowser
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
		icon = os.path.join(static_folder, 'images', 'favicon.ico')
		systray = SysTrayIcon(icon, "TorrentStats", menu_options = (('Open', None, open_browser),), 
							  on_quit=on_quit_systray, default_menu_index=0)
		systray.start()                    
	else:
		icon = os.path.join('src', 'static', 'images', 'favicon.ico')
		systray = SysTrayIcon(icon, "TorrentStats", menu_options = (('Open', None, open_browser),), 
							  on_quit=on_quit_systray, default_menu_index=0)
		systray.start()

def get_data_path():
	if sys.platform == "win32":
		return os.path.join(os.path.dirname(sys.executable), "TorrentStats")
	else:
		return os.path.join(os.getcwd(), "TorrentStats")
	
def get_db_path():
	return os.path.join(get_data_path(), "torrentstats.db")

def get_config_path():
	return os.path.join(get_data_path(), "config.ini")


def make_dicts(cursor, row):
	return dict((idx, value)
				for idx, value in enumerate(row))


# index highchart modal - return torrents active on date
@app.route('/_date_table', methods=['GET', 'POST'])
def date_table():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	r = request.get_json('data')
	series = r[0]
	tracker_id = r[1]
	client_id = r[2]
	date = r[3]

	if not tracker_id:
		if not client_id:
			if series == 0:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND th.downloaded>0",
						  (date, date + 86400))
			else:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th "
						  "ON t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND th.uploaded>0",
						  (date, date + 86400))
		else:
			if series == 0:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th "
						  "ON t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.client_id=? AND "
						  "th.downloaded>0", (date, date + 86400, client_id))
			else:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.client_id=? AND th.uploaded>0",
						  (date, date + 86400, client_id))
	else:
		if not client_id:
			if series == 0:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.tracker_id=? AND th.downloaded>0",
						  (date, date + 86400, tracker_id))
			else:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.tracker_id=? AND th.uploaded>0",
						  (date, date + 86400, tracker_id))
		else:
			if series == 0:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.tracker_id=? AND t.client_id=? "
						  "AND th.downloaded>0", (date, date + 86400, tracker_id, client_id))
			else:
				c.execute("SELECT t.id, t.hidden, t.name, th.downloaded, th.uploaded, th.total_downloaded, "
						  "th.total_uploaded, th.ratio, t.size, th.progress, trackers.name, clients.display_name, "
						  "t.status, t.directory FROM (((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) "
						  "INNER JOIN clients ON t.client_id = clients.id) INNER JOIN torrent_history th ON "
						  "t.id = th.torrent_id) WHERE th.date BETWEEN ? AND ? AND t.tracker_id=? AND t.client_id=? "
						  "AND th.uploaded>0", (date, date + 86400, tracker_id, client_id))

	rows = c.fetchall()
	conn.commit()
	conn.close()

	return jsonify(data=rows)


@app.route('/_hide_torrents', methods=['GET', 'POST'])
def hide_torrents():
	conn = sqlite3.connect(get_db_path())
	c = conn.cursor()

	r = request.get_json('data')
	hide = []
	for i in r['list']:
		hide.append((i,))
	c.executemany("UPDATE torrents SET hidden = ((hidden | 1) - (hidden & 1)) WHERE id=?", hide)
	conn.commit()
	conn.close()
	# pull in name too
	# for torrent in hide:
		# log = "'" + torrent['name'] + "' toggled hidden"
		# o.print_to_log(log, o.logger)

	return 'OK'


@app.route('/_delete_torrents', methods=['GET', 'POST'])
def delete_torrents():
	conn = sqlite3.connect(get_db_path())
	c = conn.cursor()

	r = request.get_json('data')
	delete = []
	trackers = []
	for i in r['list']:
		delete.append((i,))
	for torrent in delete:
		get_tracker_id = c.execute("SELECT tracker_id FROM torrents WHERE id=?", torrent)
		trackers.append(get_tracker_id.fetchall()[0])

	c.executemany("DELETE FROM torrents WHERE id=?", delete)
	c.executemany("DELETE FROM torrent_history WHERE torrent_id=?", delete)
	c.executemany("DELETE FROM trackers WHERE id=? AND NOT EXISTS (SELECT id FROM torrents WHERE torrents.tracker_id = "
				  "trackers.id)", trackers)

	conn.commit()
	conn.close()

	return 'OK'


# torrents page - return full torrents list
@app.route('/_full_table')
def full_table():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	c.execute("SELECT t.id, t.hidden, t.name, t.size, th.progress, th.total_downloaded, th.total_uploaded, th.ratio, "
			  "trackers.name, th.date, t.added_date, clients.display_name, t.status, t.directory, MAX(th.date) FROM "
			  "(((torrents t INNER JOIN trackers ON t.tracker_id = trackers.id) INNER JOIN clients ON t.client_id = "
			  "clients.id) INNER JOIN torrent_history th ON t.id = th.torrent_id) GROUP BY th.torrent_id")
	rows = c.fetchall()
	
	conn.commit()
	conn.close()

	return jsonify(data=rows)


# torrents page modal - return history for a single torrent
@app.route('/_single_history_table', methods=['GET', 'POST'])
def single_history_table():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	r = request.get_json('data')
	c.execute("SELECT th.date, th.progress, th.downloaded, th.uploaded, th.total_downloaded, th.total_uploaded, "
			  "th.ratio FROM torrent_history th WHERE torrent_id=? AND date IS NOT NULL", (r,))
	rows = c.fetchall()

	conn.commit()
	conn.close()

	return jsonify(data=rows)


# graphs - return tracker and client ids and names for dropdowns
@app.route('/_trackers_clients')
def trackers_clients():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	c.execute("SELECT * FROM trackers ORDER BY name")

	rows = c.fetchall()
	trackers = []
	for row in rows:
		c.execute("SELECT COUNT(id), COUNT(CASE hidden WHEN 0 THEN 1 ELSE null END) FROM torrents WHERE tracker_id=?",
				  (row[0],))
		check_hidden = c.fetchall()[0]
		if check_hidden[0] == check_hidden[1]:
			trackers.append({0: row[0], 1: ""})
		else:
			trackers.append({0: row[0], 1: row[1]})

	c.execute("SELECT id, display_name FROM clients ORDER BY display_name")
	clients = c.fetchall()

	conn.commit()
	conn.close()
	to_return = (trackers, clients)
	return jsonify(data=to_return)


# get daily upload/download stats
@app.route('/_get_chart_data', methods=['GET', 'POST'])
def get_chart_data():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	r = request.get_json('data')

	if str(r['data'][0]).isdigit():
		d = (datetime.combine(datetime.today(), time.min)) - timedelta(days=int(r['data'][0]) - 1)
		date_limit = datetime.timestamp(d)
		tracker_id = r['data'][1]
		client_id = r['data'][2]

		if not tracker_id:
			if not client_id:
				c.execute("SELECT strftime('%Y/%m/%d', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded),"
						  " SUM(uploaded) FROM torrent_history WHERE date>? GROUP BY d ORDER BY date DESC",
						  (date_limit,))
			else:
				c.execute("SELECT strftime('%Y/%m/%d', datetime(th.date, 'unixepoch', 'localtime')) AS d, "
						  "SUM(th.downloaded), SUM(th.uploaded) FROM torrent_history th INNER JOIN torrents t ON "
						  "th.torrent_id = t.id WHERE th.date>? AND t.client_id=? GROUP BY d ORDER BY th.date DESC",
						  (date_limit, client_id))
		else:
			if not client_id:
				c.execute("SELECT strftime('%Y/%m/%d', datetime(th.date, 'unixepoch', 'localtime')) AS d, "
						  "SUM(th.downloaded), SUM(th.uploaded) FROM torrent_history th INNER JOIN torrents t ON "
						  "th.torrent_id = t.id WHERE th.date>? AND t.tracker_id=? GROUP BY d ORDER BY th.date DESC",
						  (date_limit, tracker_id))
			else:
				c.execute("SELECT strftime('%Y/%m/%d', datetime(th.date, 'unixepoch', 'localtime')) AS d, "
						  "SUM(th.downloaded), SUM(th.uploaded) FROM torrent_history th INNER JOIN torrents t ON "
						  "th.torrent_id = t.id WHERE th.date>? AND t.tracker_id=? AND t.client_id=? GROUP BY d ORDER "
						  "BY th.date DESC", (date_limit, tracker_id, client_id))

		daily_data = c.fetchall()
		daily_max = 0
		trackers = []
		tracker_max = 0
		full_list = []
		today = datetime.today()
		num_days = int(r['data'][0])

		if not daily_data:
			return "OK"
		else:
			# fill in empty days for daily data
			i = 0
			for x in range(num_days):
				if i < len(daily_data):
					record = datetime.strptime(daily_data[i][0], '%Y/%m/%d')
					if daily_data[i][0] != today.strftime("%Y/%m/%d"):
						full_list.append((today.strftime("%Y/%m/%d"), 0, 0))
					else:
						full_list.append((record.strftime("%Y/%m/%d"), daily_data[i][1], daily_data[i][2]))
						i += 1
				else:
					full_list.append((today.strftime("%Y/%m/%d"), 0, 0))
				today = today - timedelta(days=1)

			full_list.reverse()
			# find the max value of both columns
			daily_max = max(max(daily_data, key=itemgetter(1))[1], max(daily_data, key=itemgetter(2))[2])

			# get the data for the tracker chart
			if not client_id:
				c.execute("SELECT trackers.id, trackers.name, SUM(th.downloaded), SUM(th.uploaded), "
						  "SUM(th.downloaded+th.uploaded) AS total FROM ((torrents t INNER JOIN trackers ON "
						  "t.tracker_id = trackers.id) INNER JOIN torrent_history th ON t.id = th.torrent_id) WHERE "
						  "th.date>? GROUP BY t.tracker_id ORDER BY total DESC LIMIT 6", (date_limit,))
			else:
				c.execute("SELECT trackers.id, trackers.name, SUM(th.downloaded), SUM(th.uploaded), "
						  "SUM(th.downloaded+th.uploaded) AS total FROM ((torrents t INNER JOIN trackers ON "
						  "t.tracker_id = trackers.id) INNER JOIN torrent_history th ON t.id = th.torrent_id) WHERE "
						  "th.date>? AND t.client_id=? GROUP BY t.tracker_id ORDER BY total DESC LIMIT 6",
						  (date_limit, client_id))

			tracker_data = c.fetchall()
			tracker_max = max(max(tracker_data, key=itemgetter(2))[2], max(tracker_data, key=itemgetter(3))[3])

			# append results to another list, hiding necessary trackers
			trackers = []
			for row in tracker_data:
				c.execute("SELECT COUNT(id), COUNT(CASE hidden WHEN 0 THEN 1 ELSE null END) FROM torrents WHERE "
						  "tracker_id=?", (row[0],))
				check_hidden = c.fetchall()[0]
				if check_hidden[0] == check_hidden[1]:
					trackers.append({0: " ", 1: row[2], 2: row[3]})
				else:
					trackers.append({0: row[1], 1: row[2], 2: row[3]})

		conn.commit()
		conn.close()
		to_return = (full_list, daily_max, trackers, tracker_max)
		return jsonify(data=to_return)
	else:
		return "OK"


# return monthly usage
def monthly_chart(c):
	c.execute("SELECT strftime('%Y-%m-01', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded), "
			  "SUM(uploaded) FROM torrent_history GROUP BY d ORDER BY date DESC")
	rows = c.fetchall()
	
	if rows:
		new_rows = []
		i = 1
		num_months = 5

		# if new database with no history, don't calculate anything. just return
		if len(rows) < 2:
			return "OK"
		
		current = datetime.fromisoformat(rows[0][0])
		prev_month = ""
		if rows[i][0]:
			prev_month = datetime.fromisoformat(rows[i][0])

		new_rows.append((current.strftime("%Y/%m/%d"), rows[0][1], rows[0][2]))
		last_month = current

		for x in range(num_months):
			end_last_month = last_month - timedelta(days=1)
			last_month = end_last_month.replace(day=1)

			if prev_month:
				if not (last_month.month == prev_month.month) or not (last_month.year == prev_month.year):
					new_rows.append((last_month.strftime("%Y/%m/%d"), 0, 0))
				else:
					new_rows.append((prev_month.strftime("%Y/%m/%d"), rows[i][1], rows[i][2]))
					i += 1
					if i >= num_months:
						break
					else:
						if rows[i][0]:
							prev_month = datetime.fromisoformat(rows[i][0])
			else:
				new_rows.append((last_month.strftime("%Y/%m/%d"), 0, 0))

		new_rows.reverse()
		return new_rows
	else:
		return rows
		
@app.route('/_all_time_table', methods=['GET', 'POST'])
def all_time_table():
	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	
	all_time = []
	r = request.get_json('data')

	if r == 24:
		c.execute("SELECT strftime('%Y/%m/%d', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded) AS "
				  "down, SUM(uploaded) AS up, (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d "
				  "ORDER BY down DESC LIMIT 1")
		down = c.fetchone()
		if down:
			all_time.append(("Downloaded", down[0], down[1], down[2], down[3]))
			
			c.execute("SELECT strftime('%Y/%m/%d', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded) AS "
					  "down, SUM(uploaded) AS up, (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d "
					  "ORDER BY up DESC LIMIT 1")
			up = c.fetchone()
			all_time.append(("Uploaded", up[0], up[1], up[2], up[3]))
			
			c.execute("SELECT strftime('%Y/%m/%d', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded), "
					  "SUM(uploaded), (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d ORDER BY total "
					  "DESC LIMIT 1")
			total = c.fetchone()
			all_time.append(("Total", total[0], total[1], total[2], total[3]))
		
	elif r == 30:
		c.execute("SELECT strftime('%Y/%m', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded) AS down, "
			      "SUM(uploaded) AS up, (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d ORDER BY "
				  "down DESC LIMIT 1")
		down = c.fetchone()
		if down:
			all_time.append(("Downloaded", down[0], down[1], down[2], down[3]))

			c.execute("SELECT strftime('%Y/%m', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded) AS down, "
					  "SUM(uploaded) AS up, (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d ORDER BY "
					  "up DESC LIMIT 1")

			up = c.fetchone()
			all_time.append(("Uploaded", up[0], up[1], up[2], up[3]))

			c.execute("SELECT strftime('%Y/%m', datetime(date, 'unixepoch', 'localtime')) AS d, SUM(downloaded), "
					  "SUM(uploaded), (SUM(downloaded+uploaded)) AS total FROM torrent_history GROUP BY d ORDER BY total "
					  "DESC LIMIT 1")

			total = c.fetchone()
			all_time.append(("Total", total[0], total[1], total[2], total[3]))
	
	conn.commit()
	conn.close()
	
	return jsonify(data=all_time)


@app.route('/_update_general', methods=['GET', 'POST'])
def update_general():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	if r['settings'][0] == "default":
		l = locale.getdefaultlocale()
		port = 5656
		config.set('Preferences', 'locale', l[0])
		config.set('Preferences', 'port', str(port))
		with open(get_config_path(), 'w') as config_file:
			config.write(config_file)
		data = (l[0], port)
		return jsonify(data=data)
	else:
		config.set('Preferences', 'locale', r['settings'][0])
		config.set('Preferences', 'port', r['settings'][1])
		with open(get_config_path(), 'w') as config_file:
			config.write(config_file)

	return jsonify(data="OK")


@app.route('/_update_win', methods=['GET', 'POST'])
def update_win():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')
	
	if r['settings'][0] == 'yes':
		win_functions.add_to_startup()
	elif r['settings'][0] == 'no':
		win_functions.remove_startup()
	
	if r['settings'][1] == 'yes':
		win_functions.add_to_start_menu()
	elif r['settings'][1] == 'no':
		win_functions.remove_start_menu()

	config.set('Preferences', 'start_at_login', r['settings'][0])
	config.set('Preferences', 'start_menu_shortcut', r['settings'][1])

	with open(get_config_path(), 'w') as config_file:
		config.write(config_file)

	return jsonify(data="OK")


@app.route('/_update_tasks', methods=['GET', 'POST'])
def update_tasks():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	old_tcf = config['Preferences']['torrent_check_frequency']
	old_bf = config['Preferences']['backup_frequency']
	old_dcf = config['Preferences']['deleted_check_frequency']
	
	new_tcf = r['tasks'][0]
	new_bf = r['tasks'][1]
	new_dcf = r['tasks'][2]

	updated_jobs = []
	log = ""
	separator = " | "
	if old_tcf != new_tcf:
		config.set('Preferences', 'torrent_check_frequency', new_tcf)
		updated_jobs.append((1, int(new_tcf)))
		log = "1: {oldtcf}->{newtcf}".format(oldtcf=old_tcf, newtcf=new_tcf)
	if old_bf != new_bf:
		config.set('Preferences', 'backup_frequency', new_bf)
		updated_jobs.append((2, int(new_bf)))
		if log:
			log = "{log}{separator}2: {oldbf}->{newbf}".format(log=log, separator=separator, oldbf=old_bf, newbf=new_bf)
		else:
			log = "2: {oldbf}->{newbf}".format(oldbf=old_bf, newbf=new_bf)       
	if old_dcf != new_dcf:
		config.set('Preferences', 'deleted_check_frequency', new_dcf)
		updated_jobs.append((3, int(new_dcf)))
		if log:
			log = "{log}{separator}3: {olddcf}->{newdcf}".format(log=log, separator=separator, olddcf=old_dcf, 
															   newdcf=new_dcf)
		else:
			log = "3: {olddcf}->{newdcf}".format(olddcf=old_dcf, newdcf=new_dcf)
	log = "Task Preferences Updated. {log}".format(log=log)
	
	with open(get_config_path(), 'w') as config_file:
		config.write(config_file)

	o.update_jobs(updated_jobs, o.scheduler, log, o.logger)
	
	return jsonify(data="OK")


@app.route('/_clients_table')
def clients_table():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	clients = []
	for section in config:
		if 'Client' in section:
			active_client = 0
			if config[section]['sync'] == 'yes':
				active_client = client_connect.test_client(config[section]['ip'], config[section]['user'],
														   config[section]['pass'], config[section]['client_type'])
			else:
				active_client = 7
			clients.append((section, config[section]['display_name'], config[section]['client_name'],
							config[section]['ip'], config[section]['user'], config[section]['pass'], active_client))

	return jsonify(data=clients)
	
@app.route('/_sync_setting', methods=['GET', 'POST'])
def sync_setting():
	config = configparser.ConfigParser()
	config.read(get_config_path())
	
	client = request.get_json('data')
	change = ""
	
	if config[client['section']]['sync'] == 'yes':
		config.set(client['section'], 'sync', 'no')
		change = "paused"
	else:
		config.set(client['section'], 'sync', 'yes')
		change = "resumed"
	
	with open(get_config_path(), 'w') as config_file:
				config.write(config_file)
				
	return jsonify(data=change)

@app.route('/_client_edit', methods=['GET', 'POST'])
def client_edit():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	for section in config:
		if 'Client' in section:
			if r['data'][0] != section:
				if r['data'][2] == config[section]['ip']:
					return jsonify(data=4)
				if r['data'][1] == config[section]['display_name']:
					return jsonify(data=5)

	if r['data'][2]:
		client_type = client_connect.identify_client(r['data'][2], r['data'][3], r['data'][4])

		if str(client_type).isdigit():
			return jsonify(data=client_type)
		else:
			if config[r['data'][0]]['display_name'] != r['data'][1]:
				config.set(r['data'][0], 'display_name', r['data'][1])

				conn = sqlite3.connect(get_db_path())
				conn.row_factory = make_dicts

				c = conn.cursor()
				c.execute("UPDATE clients SET display_name=? WHERE section_name=?", (r['data'][1], r['data'][0]))
				conn.commit()
				conn.close()

			config.set(r['data'][0], 'ip', r['data'][2])
			config.set(r['data'][0], 'user', r['data'][3])
			config.set(r['data'][0], 'pass', r['data'][4])

			with open(get_config_path(), 'w') as config_file:
				config.write(config_file)

			return jsonify(data="OK")
	else:
		return jsonify(data=6)


@app.route('/_client_delete', methods=['GET', 'POST'])
def client_delete():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	config.remove_section(r['client'])
	with open(get_config_path(), 'w') as config_file:
		config.write(config_file)

	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	get_ids = c.execute("SELECT torrents.id FROM torrents INNER JOIN clients ON torrents.client_id = clients.id WHERE "
						"clients.section_name=?", (r['client'],))
	to_delete = []
	for id in get_ids.fetchall():
		to_delete.append((id[0],))

	c.executemany("DELETE FROM torrent_history WHERE torrent_id=?", to_delete)
	c.executemany("DELETE FROM torrents WHERE id=?", to_delete)
	c.execute("DELETE FROM clients WHERE section_name=?", (r['client'],))

	conn.commit()
	conn.close()

	return jsonify(data="OK")


@app.route('/_client_add_verify', methods=['GET', 'POST'])
def client_add_verify():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	section_num = 1
	for section in config:
		if 'Client' in section:
			section_num = int(section.rpartition(".")[2]) + 1
			if r['data'][0] == config[section]['ip']:
				return jsonify(data=4)

	if r['data'][0]:
		client_type = client_connect.identify_client(r['data'][0], r['data'][1], r['data'][2])

		if str(client_type).isdigit():
			return jsonify(data=client_type)
		else:
			client_info = (str(section_num) + ": " + client_type[1], client_type[1], client_type[0])
			return jsonify(data=client_info)

	return "OK"


@app.route('/_client_add', methods=['GET', 'POST'])
def client_add():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	r = request.get_json('data')

	section_num = 1
	for section in config:
		if 'Client' in section:
			section_num = int(section.rpartition(".")[2]) + 1
			if r['data'][0] == config[section]['display_name']:
				return jsonify(data=5)

	client_section = 'Client.' + str(section_num)

	config.add_section(client_section)
	config.set(client_section, 'display_name', r['data'][0])
	config.set(client_section, 'client_name', r['data'][1])
	config.set(client_section, 'ip', r['data'][2])
	config.set(client_section, 'user', r['data'][3])
	config.set(client_section, 'pass', r['data'][4])
	config.set(client_section, 'client_type', r['data'][5])
	config.set(client_section, 'sync', 'yes')

	with open(get_config_path(), 'w') as config_file:
		config.write(config_file)

	return jsonify(data="OK")
	
@app.route('/_client_add_torrents')
def client_add_torrents():
	o.multiple_frequent_checks(o.ts_db, o.config_file, o.scheduler, o.logger)
	
	return jsonify(data="OK")

@app.route('/_refresh_torrents')
def refresh_torrents():
	o.multiple_frequent_checks(o.ts_db, o.config_file, o.scheduler, o.logger)
	o.multiple_update_info(o.ts_db, o.config_file, o.logger)
	
	return jsonify(data="OK")

@app.route('/_resync')
def resync():
	o.initial_start(o.data_dir, o.ts_db, o.config_file, o.logger)
	
	return jsonify(data="OK")

@app.route('/')
@app.route('/index')
def index():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	conn = sqlite3.connect(get_db_path())
	conn.row_factory = make_dicts

	c = conn.cursor()
	month_chart = monthly_chart(c)
	return render_template('index.html', title='Home', locale=config['Preferences']['locale'],
						   monthly_chart=month_chart)


@app.route('/torrents')
def torrents():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	return render_template('torrents.html', title='Torrents', locale=config['Preferences']['locale'])


@app.route('/settings')
def settings():
	config = configparser.ConfigParser()
	config.read(get_config_path())

	preferences = (config['Preferences']['locale'], config['Preferences']['torrent_check_frequency'],
				   config['Preferences']['backup_frequency'], config['Preferences']['deleted_check_frequency'],
				   config['Preferences']['start_at_login'], config['Preferences']['start_menu_shortcut'],
				   config['Preferences']['port'])

	return render_template('settings.html', title='Settings', preferences=preferences,
						   locale=config['Preferences']['locale'])
