import sqlite3
import os, os.path, sys
import configparser
# import signal
import logging
import time, locale
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import date, datetime, timedelta
from tzlocal import get_localzone
from bisect import bisect_left
# from urllib.parse import urlparse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers import cron
from src import client_connect

if sys.platform == "win32":
	from src import win_functions


class ManageDB:
	def __init__(self):
		self.data_dir = ""
		if sys.platform == "win32":
			self.data_dir = os.path.join(os.path.dirname(sys.executable), "TorrentStats")
		else:
			self.data_dir = os.path.join(os.getcwd(), "TorrentStats")

		self.log_dir = os.path.join(self.data_dir, "logs")

		Path(self.log_dir).mkdir(parents=True, exist_ok=True)
		Path(os.path.join(self.data_dir, "backup")).mkdir(parents=True, exist_ok=True)

		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)

		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

		file_handler = RotatingFileHandler(os.path.join(self.log_dir, "log.log"), maxBytes=102400, backupCount=5,
										   encoding='utf-8')
		file_handler.setFormatter(formatter)
		file_handler.setLevel(logging.DEBUG)
		self.logger.addHandler(file_handler)

		self.logger.info("Application started")

		tz = str(get_localzone())
		# self.scheduler = BlockingScheduler()
		self.scheduler = BackgroundScheduler(timezone=tz)
		
		self.ts_db = os.path.join(self.data_dir, "torrentstats.db")
		self.config_file = os.path.join(self.data_dir, "config.ini")
		if os.path.isfile(self.ts_db) == False:
			self.first_start(self.ts_db, self.config_file, self.logger)
		else:
			self.initial_start(self.data_dir, self.ts_db, self.config_file, self.logger)
		
		config = configparser.ConfigParser()
		config.read(self.config_file)
		
		self.t_check_frequency = config['Preferences']['torrent_check_frequency']
		self.backup_frequency = config['Preferences']['backup_frequency']
		self.d_check_frequency = config['Preferences']['deleted_check_frequency']

		trigger = cron.CronTrigger(hour='*', minute='*/' + self.t_check_frequency, timezone=tz)
		self.scheduler.add_job(self.multiple_frequent_checks, trigger=trigger, args=[self.ts_db, self.config_file,
							   self.scheduler, self.logger], misfire_grace_time=30, id='1')

		trigger = cron.CronTrigger(day_of_week='*/' + self.backup_frequency, hour='0', minute='1', second='45', 
								   timezone=tz)
		self.scheduler.add_job(self.backup_database, trigger=trigger, args=[self.data_dir, self.ts_db, self.logger], 
							   misfire_grace_time=30, id='2')

		if int(self.d_check_frequency) > 59:
			trigger = cron.CronTrigger(hour='*', minute='0', second='30', timezone=tz)
			self.scheduler.add_job(self.multiple_update_info, trigger=trigger, args=[self.ts_db, self.config_file, 
								   self.logger], misfire_grace_time=30, id='3')
		else:
			trigger = cron.CronTrigger(hour='*', minute='*/' + self.d_check_frequency, second='30', timezone=tz)
			self.scheduler.add_job(self.multiple_update_info, trigger=trigger, args=[self.ts_db, self.config_file, 
								   self.logger], misfire_grace_time=30, id='3')

		trigger = cron.CronTrigger(hour='*/4', minute='0', second='15', timezone=tz)
		self.scheduler.add_job(self.multiple_update_client_version, trigger=trigger, args=[self.config_file, 
							   self.logger], misfire_grace_time=30, id='4')

		self.scheduler.start()

	def print_to_log(self, log, logger):
		logger.info(log)

	def close_ts(self, ts_db, config_file, scheduler, logger):
		self.multiple_frequent_checks(ts_db, config_file, scheduler, logger)
		if sys.platform == "win32":
			config = configparser.ConfigParser()
			config.read(config_file)
			self.verify_win_options(config)
		scheduler.shutdown()
		logger.info("Closing application")
		os._exit(0)

	# Create database file and add tables
	def first_start(self, ts_db, config_file, logger):
		# create log file
		logger.info("No database exists. Creating...")

		conn = sqlite3.connect(ts_db)
		c = conn.cursor()

		c.execute("""CREATE TABLE trackers (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL
					)
					""")

		c.execute("""CREATE TABLE clients (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					section_name TEXT NOT NULL,
					display_name TEXT NOT NULL
					)
					""")

		c.execute("""CREATE TABLE torrents (
					id INTEGER PRIMARY KEY AUTOINCREMENT, 
					name TEXT NOT NULL,
					tracker_id INTEGER NOT NULL,
					client_id INTEGER NOT NULL,
					added_date INTEGER,
					status TEXT NOT NULL,
					directory TEXT,
					size INTEGER NOT NULL,
					hash TEXT NOT NULL,
					hidden INTEGER NOT NULL,
					FOREIGN KEY (tracker_id) REFERENCES trackers (id),
					FOREIGN KEY (client_id) REFERENCES clients (id)
					)
					""")

		c.execute("""CREATE TABLE torrent_history (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					torrent_id INTEGER NOT NULL,
					date INTEGER,
					downloaded INTEGER,
					uploaded INTEGER,
					total_downloaded INTEGER,
					total_uploaded INTEGER,
					progress REAL NOT NULL,
					ratio REAL NOT NULL,
					FOREIGN KEY (torrent_id) REFERENCES torrents (id)
					)
					""")

		c.execute("""CREATE TABLE lists (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL
					)
					""")

		c.execute("""CREATE TABLE torrents_lists (
					torrents_id INTEGER NOT NULL,
					lists_id INTEGER NOT NULL,
					FOREIGN KEY (torrents_id) REFERENCES torrents (id),
					FOREIGN KEY (lists_id) REFERENCES lists (id)
					)
					""")

		conn.commit()
		conn.close()

		config = configparser.ConfigParser()
		l = locale.getdefaultlocale()
		start_at_login = start_menu = "0"
		if sys.platform == "win32":
			start_at_login = start_menu = "2"
		port = "5656"
		config['Preferences'] = {'locale': l[0],
								 'torrent_check_frequency': '5',
								 'backup_frequency': '1',
								 'deleted_check_frequency': '30',
								 'start_at_login': start_at_login,
								 'start_menu_shortcut': start_menu,
								 'port': port}

		with open(config_file, 'w') as config_new:
			config.write(config_new)

		logger.info("Database created and application locale set to '" + l[0] + "'")

	# add all torrents from client when client is first added
	def add_client_to_db(self, ts_db, client_torrents, display_name, client_name, section_name, client_type, ip,
						 user, pw, logger):
		logger.info("New client detected: '" + display_name + "' (" + client_name + "). Adding to DB...")

		conn = sqlite3.connect(ts_db)
		c = conn.cursor()

		# fill client table
		c.execute("INSERT INTO clients VALUES (NULL,?,?)", (section_name, display_name))

		select_client_id = c.execute("SELECT id FROM clients WHERE section_name=?", (section_name,))
		client_id = select_client_id.fetchone()

		torrents_table = []
		history_table = []

		qbit_cookie = []
		# login to qbit and get cookie
		if client_type == 'qbittorrent':
			qbit_cookie = client_connect.get_qbit_cookie(ip, user, pw, display_name, client_name, logger)

		# fill tracker table
		for torrent in client_torrents:
			# need to get tracker for qbittorrent
			if client_type == 'qbittorrent':
				torrent['tracker'] = client_connect.get_qbit_tracker(torrent['hash'], qbit_cookie, ip, display_name,
																	 client_name, logger)

			get_tracker_id = c.execute("SELECT id FROM trackers WHERE name=?", (torrent['tracker'],))
			tracker_id = get_tracker_id.fetchone()

			# if tracker doesn't exist, insert new entry into trackers table
			if not tracker_id:
				c.execute("INSERT INTO trackers VALUES (NULL,?)", (torrent['tracker'],))
				logger.info("New tracker. Added '" + torrent['tracker'] + "' to database")

		# fill torrents table next
		for torrent in client_torrents:
			# need to get the trackerID again
			select_tracker_id = c.execute("SELECT id FROM trackers WHERE name=?", (torrent['tracker'],))
			tracker_id = select_tracker_id.fetchone()

			# entry = name / tracker id / client id / added date / status / directory / selected size / hash / hidden
			torrents_entry = (torrent['name'], tracker_id[0], client_id[0], torrent['addedDate'], torrent['state'],
							  torrent['downloadDir'], torrent['size'], torrent['hash'], 1)

			torrents_table.append(torrents_entry)
		c.executemany("INSERT INTO torrents VALUES (NULL,?,?,?,?,?,?,?,?,?)", torrents_table)

		# fill torrent_history table
		for torrent in client_torrents:
			get_torrent_id = c.execute("SELECT id FROM torrents WHERE client_id=? AND hash=?", (client_id[0],
																								torrent['hash']))
			torrent_id = get_torrent_id.fetchone()
			# entry = torrents id / date / downloaded / uploaded / total downloaded / total uploaded / progress / ratio
			history_entry = (torrent_id[0], None, None, None, torrent['downloaded'], torrent['uploaded'],
							 torrent['progress'], torrent['ratio'])
			history_table.append(history_entry)
		c.executemany("INSERT INTO torrent_history VALUES (NULL,?,?,?,?,?,?,?,?)", history_table)

		conn.commit()
		conn.close()
		logger.info("'" + display_name + "' and all torrents successfully added to DB")

	# add recently changed to DB
	def add_to_db(self, torrent, display_name, client_name, section_name, client_type, start_today, qbit_cookie, ip, c,
				  logger):
		# need to get tracker for qbittorrent
		if client_type == 'qbittorrent':
			torrent['tracker'] = client_connect.get_qbit_tracker(torrent['hash'], qbit_cookie, ip, display_name,
																 client_name, logger)

		select_client_id = c.execute("SELECT id FROM clients WHERE section_name=?", (section_name,))
		client_id = select_client_id.fetchone()

		if not client_id:
			logger.error("Client not found in DB. Can't add torrent")
			return

		select_torrent_id = c.execute("SELECT id FROM torrents WHERE client_id=? AND hash=? AND added_date=?",
									  (client_id[0], torrent['hash'], torrent['addedDate']))
		torrent_id = select_torrent_id.fetchone()

		# if there's no matching entry in the torrents table, it must be a new torrent, so we'll need to add it to
		# the DB
		if not torrent_id:
			# first need to check if tracker already exists in tracker table
			get_tracker_id = c.execute("SELECT id FROM trackers WHERE name=?", (torrent['tracker'],))
			tracker_id = get_tracker_id.fetchone()

			# if tracker doesn't exist, insert new entry into trackers table
			if not tracker_id:
				c.execute("INSERT INTO trackers VALUES (NULL,?)", (torrent['tracker'],))
				logger.info("'" + display_name + "': New tracker. Added '" + torrent['tracker'] + "' to database")
				get_tracker_id = c.execute("SELECT id FROM trackers WHERE name=?", (torrent['tracker'],))
				tracker_id = get_tracker_id.fetchone()

			# entry = name / tracker id / client id / added_date / status / directory / selected size / hash / hidden
			c.execute("INSERT INTO torrents VALUES (NULL,?,?,?,?,?,?,?,?,?)", (torrent['name'], tracker_id[0],
																			   client_id[0], torrent['addedDate'],
																			   torrent['state'], torrent['downloadDir'],
																			   torrent['size'], torrent['hash'], 1))

			get_torrent_id = c.execute("SELECT id FROM torrents WHERE client_id=? AND hash=? AND added_date=?",
									   (client_id[0], torrent['hash'], torrent['addedDate']))
			torrent_id = get_torrent_id.fetchone()
		else:
			# update status and size
			c.execute("UPDATE torrents SET status=?, size=? WHERE id=?", (torrent['state'], torrent['size'],
																		  torrent_id[0]))

		# make variables for logs
		log_name = "'" + torrent['name'] + "'"
		log_dl = log_t_dl = str(torrent['downloaded'])
		log_ul = log_t_ul = str(torrent['uploaded'])

		fetch_recent = c.execute("SELECT id, total_downloaded, total_uploaded, progress FROM torrent_history WHERE "
								 "torrent_id=? AND date>=?", (torrent_id[0], start_today))
		recent = fetch_recent.fetchone()

		fetch_history = c.execute("SELECT total_downloaded, total_uploaded FROM torrent_history WHERE torrent_id=? AND "
								  "(date<? OR date IS NULL) ORDER BY id DESC LIMIT 1", (torrent_id[0], start_today))
		history = fetch_history.fetchone()

		if client_type == 'deluge':
			entry = ()
			torrent['activityDate'] = time.time()
			# at 00:00 check, the activity date will be logged as the next day when using time.time(). Subtract a
			# couple of minutes to correct
			if not int(datetime.fromtimestamp(torrent['activityDate']).strftime('%H%M')):
				torrent['activityDate'] = torrent['activityDate'] - 90

			# if there's no historical or recent history (brand new torrent), add a new entry with latest stats
			# entry = torrents id / date / downloaded / uploaded / total downloaded / total uploaded / progress / ratio
			if not recent:
				if not history:
					log_name = "+" + log_name
					if torrent['downloaded']:
						log_dl = log_t_dl = "+" + log_dl
					if torrent['uploaded']:
						log_ul = log_t_ul = "+" + log_ul

					entry = (torrent_id[0], torrent['activityDate'], torrent['downloaded'], torrent['uploaded'],
							 torrent['downloaded'], torrent['uploaded'], torrent['progress'], torrent['ratio'])

				# if there's no recent but is a historical (first of the day), add a new entry
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					if downloaded:
						log_dl = "+" + str(downloaded)
						log_t_dl = "+" + log_t_dl
					if uploaded:
						log_ul = "+" + str(uploaded)
						log_t_ul = "+" + log_t_ul

					entry = (torrent_id[0], torrent['activityDate'], downloaded, uploaded, torrent['downloaded'],
							 torrent['uploaded'], torrent['progress'], torrent['ratio'])

				c.execute("INSERT INTO torrent_history VALUES (NULL,?,?,?,?,?,?,?,?)", entry)

			# if there's historical and recent history (multiple times today of old torrent),
			# update the entry with latest stats
			else:
				recent_down = torrent['downloaded'] - recent[1]
				recent_up = torrent['uploaded'] - recent[2]

				if recent_down == 0 and recent_up == 0:
					return

				# if there is a recent but not a historical, it must be an update to a new entry from today.
				if not history:
					if recent_down:
						log_dl = "+" + str(recent_down)
						log_t_dl = "+" + log_t_dl
					if recent_up:
						log_ul = "+" + str(recent_up)
						log_t_ul = "+" + log_t_ul

					entry = (torrent['activityDate'], torrent['downloaded'], torrent['uploaded'], torrent['downloaded'],
							 torrent['uploaded'], torrent['progress'], torrent['ratio'], recent[0])
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					if downloaded:
						log_dl = "+" + str(downloaded)
						log_t_dl = "+" + log_t_dl
					if uploaded:
						log_ul = "+" + str(uploaded)
						log_t_ul = "+" + log_t_ul

					entry = (torrent['activityDate'], downloaded, uploaded, torrent['downloaded'], torrent['uploaded'],
							 torrent['progress'], torrent['ratio'], recent[0])

				c.execute("UPDATE torrent_history SET date=?, downloaded=?, uploaded=?, total_downloaded=?, "
						  "total_uploaded=?, progress=?, ratio=? WHERE id=?", entry)
		else:
			if torrent['activityDate']:
				# if activityDate is 00:00, it'll get grouped as next day when pulled into tables. Subtract a couple of
				# minutes to correct
				if not int(datetime.fromtimestamp(torrent['activityDate']).strftime('%H%M')):
					torrent['activityDate'] = torrent['activityDate'] - 90

			entries = []
			# if there's no historical or recent history (brand new torrent), add a new entry with latest stats
			# entry = torrents id / date / downloaded / uploaded / total downloaded / total uploaded / progress / ratio
			if not recent:
				if not history:
					log_name = "+" + log_name
					if torrent['doneDate'] > 0:
						# if new torrent has completed since last launch and was completed before the last activity,
						# we'll assume the torrent was added and completed on the same date.
						# Insert an entry with full downloaded and 0 upload on completed date.
						# Add a second entry on the activity date with 0 down and full uploaded.
						if self.end_of_date(datetime.fromtimestamp(torrent['doneDate'])) < torrent['activityDate']:
							entries.append((torrent_id[0], torrent['doneDate'], torrent['downloaded'], 0,
											torrent['downloaded'], 0, torrent['progress'], torrent['ratio']))

							if torrent['downloaded']:
								log_dl = "+" + log_dl
							logger.info("'" + display_name + "': " + log_name + " | date:" + str(torrent['doneDate']) +
										" | 🡣:" + log_dl + "b | 🡡:0b | total🡣:" + log_dl + "b | " + "total🡡:0b")
							log_dl = "0"

							if torrent['uploaded']:
								log_ul = log_t_ul = "+" + log_ul

							entries.append((torrent_id[0], torrent['activityDate'], 0, torrent['uploaded'],
											torrent['downloaded'], torrent['uploaded'], torrent['progress'],
											torrent['ratio']))
						else:
							if torrent['downloaded']:
								log_dl = log_t_dl = "+" + log_dl
							if torrent['uploaded']:
								log_ul = log_t_ul = "+" + log_ul

							entries.append((torrent_id[0], torrent['activityDate'], torrent['downloaded'],
											torrent['uploaded'], torrent['downloaded'], torrent['uploaded'],
											torrent['progress'], torrent['ratio']))
					# if new torrent hasn't been completed, add one entry on the activity date
					else:
						if torrent['downloaded']:
							log_dl = log_t_dl = "+" + log_dl
						if torrent['uploaded']:
							log_ul = log_t_ul = "+" + log_ul

						entries.append((torrent_id[0], torrent['activityDate'], torrent['downloaded'],
										torrent['uploaded'], torrent['downloaded'], torrent['uploaded'],
										torrent['progress'], torrent['ratio']))
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					# if existing torrent has completed since last launch and was completed before the last activity,
					# we'll assume the final progress of the download was completed on the done date.
					# Insert an entry with downloaded-historyDownloaded on completed date.
					# Add a second entry on the activity date with 0 down and uploaded-historyUploaded.
					if torrent['doneDate'] > 0 and downloaded:
						if self.end_of_date(datetime.fromtimestamp(torrent['doneDate'])) < torrent['activityDate']:
							ratio_estimate = history[1] / torrent['downloaded']
							entries.append((torrent_id[0], torrent['doneDate'], downloaded, 0, torrent['downloaded'],
											history[1], torrent['progress'], ratio_estimate))

							log_dl = "+" + str(downloaded)
							log_t_dl = "+" + log_t_dl
							logger.info("'" + display_name + "': " + log_name + " | date:" + str(torrent['doneDate']) +
										" | 🡣:" + log_dl + "b | 🡡:0b | total🡣:" + log_t_dl + "b | " + "total🡡:" + 
										str(history[1]) + "b")
							log_dl = "0"
							log_t_dl = str(torrent['downloaded'])
							if uploaded:
								log_ul = "+" + str(uploaded)
								log_t_ul = "+" + log_t_ul
							else:
								log_ul = str(uploaded)

							entries.append((torrent_id[0], torrent['activityDate'], 0, uploaded, torrent['downloaded'],
											torrent['uploaded'], torrent['progress'], torrent['ratio']))
						else:
							if downloaded:
								log_dl = "+" + str(downloaded)
								log_t_dl = "+" + log_t_dl
							else:
								log_dl = str(downloaded)
							if uploaded:
								log_ul = "+" + str(uploaded)
								log_t_ul = "+" + log_t_ul
							else:
								log_ul = str(uploaded)

							entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
											torrent['downloaded'], torrent['uploaded'], torrent['progress'],
											torrent['ratio']))

					# if existing torrent hasn't been completed, add one entry on the activity date
					else:
						if downloaded:
							log_dl = "+" + str(downloaded)
							log_t_dl = "+" + log_t_dl
						else:
							log_dl = str(downloaded)
						if uploaded:
							log_ul = "+" + str(uploaded)
							log_t_ul = "+" + log_t_ul
						else:
							log_ul = str(uploaded)

						entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
										torrent['downloaded'], torrent['uploaded'], torrent['progress'],
										torrent['ratio']))

				c.executemany("INSERT INTO torrent_history VALUES (NULL,?,?,?,?,?,?,?,?)", entries)

			# if there's historical and recent history (multiple times today of old torrent), update the entry with
			# latest stats
			else:
				recent_down = torrent['downloaded'] - recent[1]
				recent_up = torrent['uploaded'] - recent[2]

				progress_diff = torrent['progress'] - recent[3]
				if not progress_diff:
					if recent_down == 0 and recent_up == 0:
						return

				# if there is a recent but not a historical, it must be an update to a new entry from today.
				if not history:
					if recent_down:
						log_dl = "+" + str(recent_down)
						log_t_dl = "+" + log_t_dl
					if recent_up:
						log_ul = "+" + str(recent_up)
						log_t_ul = "+" + log_t_ul

					entries.append((torrent['activityDate'], torrent['downloaded'], torrent['uploaded'],
									torrent['downloaded'], torrent['uploaded'], torrent['progress'],
									torrent['ratio'], recent[0]))
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					if downloaded:
						log_dl = "+" + str(downloaded)
						log_t_dl = "+" + log_t_dl
					else:
						log_dl = "0"
					if uploaded:
						log_ul = "+" + str(uploaded)
						log_t_ul = "+" + log_t_ul
					else:
						log_ul = "0"

					entries.append((torrent['activityDate'], downloaded, uploaded, torrent['downloaded'],
									torrent['uploaded'], torrent['progress'], torrent['ratio'], recent[0]))

				c.executemany("UPDATE torrent_history SET date=?, downloaded=?, uploaded=?, total_downloaded=?, "
							  "total_uploaded=?, progress=?, ratio=? WHERE id=?", entries)

		logger.info("'" + display_name + "': " + log_name + " | date:" + str(torrent['activityDate']) + " | 🡣:" +
					log_dl + "b | 🡡:" + log_ul + "b | total🡣:" + log_t_dl + "b | " + "total🡡:" + log_t_ul + "b")

	# Binary search, returning index if there's a match, else None
	def index(self, a, x):
		i = bisect_left(a, x)
		if i != len(a) and a[i] == x:
			return i
		return

	# return timestamp at start(00:00) of date for checking torrent dates
	def start_of_date(self, dt):
		start = datetime.combine(dt, datetime.min.time())
		return datetime.timestamp(start)

	# return timestamp at end(11:59:59.999) of date for checking torrents
	def end_of_date(self, dt):
		end = datetime.combine(dt, datetime.max.time())
		return datetime.timestamp(end)

	# no activity date in deluge. to find recent torrents we'll just have to check for matching hashes and
	# changes to down/up
	def check_deluge(self, c, ts_db, client_torrents, client_id):
		recent = []
		for torrent in client_torrents:
			select_search_recent = c.execute("SELECT t.id FROM torrents t INNER JOIN torrent_history th ON t.id = "
											 "th.torrent_id WHERE t.hash=? AND t.client_id=? AND t.added_date=? AND "
											 "th.total_downloaded=? AND th.total_uploaded=?", (torrent['hash'],
																							   client_id,
																							   torrent['addedDate'],
																							   torrent['downloaded'],
																							   torrent['uploaded']))
			search_recent = select_search_recent.fetchone()
			if not search_recent:
				recent.append(torrent)
		return recent

	# check for recent changes on program start, and add them to the DB
	def initial_check(self, ts_db, client_torrents, display_name, client_name, section_name, client_type, ip, user,
					  pw, logger):
		logger.info("Checking for recent activity from '" + display_name + "' (" + client_name + ")")
		conn = sqlite3.connect(ts_db)
		c = conn.cursor()

		recent_torrents = []
		select_most_recent = c.execute("SELECT date FROM torrent_history ORDER BY date DESC LIMIT 1")
		most_recent = select_most_recent.fetchone()[0]

		current_time = datetime.now()
		if current_time.hour == 0 and current_time.minute == 0:
			current_time = current_time - timedelta(seconds=90)
		start_today = self.start_of_date(current_time)

		if client_type == 'deluge':
			select_client_id = c.execute("SELECT id FROM clients WHERE section_name=?", (section_name,))
			client_id = select_client_id.fetchone()[0]
			recent_torrents = self.check_deluge(c, ts_db, client_torrents, client_id)
		else:
			for torrent in client_torrents:
				if torrent['activityDate'] > 0:
					if most_recent:
						if torrent['activityDate'] > most_recent:
							recent_torrents.append(torrent)
					else:
						if torrent['activityDate'] >= start_today:
							recent_torrents.append(torrent)

		if recent_torrents:
			qbit_cookie = None
			if client_type == 'qbittorrent':
				qbit_cookie = client_connect.get_qbit_cookie(ip, user, pw, display_name, client_name, logger)

			for torrent in recent_torrents:
				self.add_to_db(torrent, display_name, client_name, section_name, client_type, start_today, qbit_cookie,
							   ip, c, logger)

		conn.commit()
		conn.close()
		logger.info("Check complete")

	# check for recent changes at intervals
	def frequent_check(self, ts_db, client_torrents, display_name, client_name, section_name, client_type, ip, user,
					   pw, logger):
		conn = sqlite3.connect(ts_db)
		c = conn.cursor()

		current_time = datetime.now()
		if current_time.hour == 0 and current_time.minute == 0:
			current_time = current_time - timedelta(seconds=90)
		start_today = self.start_of_date(current_time)

		if client_type == 'deluge':
			select_client_id = c.execute("SELECT id FROM clients WHERE section_name=?", (section_name,))
			client_id = select_client_id.fetchone()[0]
			recent_torrents = self.check_deluge(c, ts_db, client_torrents, client_id)
			for torrent in recent_torrents:
				self.add_to_db(torrent, display_name, client_name, section_name, client_type, start_today, None, None,
							   c, logger)
		else:
			qbit_cookie = None
			if client_type == 'qbittorrent':
				qbit_cookie = client_connect.get_qbit_cookie(ip, user, pw, display_name, client_name, logger)

			for torrent in client_torrents:
				if torrent['activityDate'] >= start_today:
					self.add_to_db(torrent, display_name, client_name, section_name, client_type, start_today,
								   qbit_cookie, ip, c, logger)

		conn.commit()
		conn.close()

	# when we have multiple clients, use this method to call frequent checks for each one, one after another
	# read the config file fresh every time, to account for new clients
	def multiple_frequent_checks(self, ts_db, config_file, scheduler, logger):
		config = configparser.ConfigParser()
		config.read(config_file)

		# get all existing client names from the DB
		conn = sqlite3.connect(ts_db)
		c = conn.cursor()
		select_clients = c.execute("SELECT section_name FROM clients")
		clients_list = select_clients.fetchall()
		existing_clients = []
		for client in clients_list:
			existing_clients.append(client[0])

		# do a check on each client. If it's a new client, add it
		for section in config:
			if 'Client' in section:
				client_torrents = client_connect.get_torrents(config[section]['ip'], config[section]['user'],
															  config[section]['pass'], config[section]['client_type'],
															  config[section]['display_name'],
															  config[section]['client_name'], logger)
				if client_torrents:
					if section not in existing_clients:
						self.add_client_to_db(ts_db, client_torrents, config[section]['display_name'],
											  config[section]['client_name'], section, config[section]['client_type'],
											  config[section]['ip'], config[section]['user'], config[section]['pass'],
											  logger)
					self.frequent_check(ts_db, client_torrents, config[section]['display_name'],
										config[section]['client_name'], section, config[section]['client_type'],
										config[section]['ip'], config[section]['user'], config[section]['pass'], logger)

		conn.commit()
		conn.close()
	
	# reschedule jobs when user updates preferences
	def update_jobs(self, updated_jobs, scheduler, log, logger):
		logger.info(log)
		for job in updated_jobs:
			if job[0] == 1:
				trigger = cron.CronTrigger(hour='*', minute='*/' + str(job[1]))
				scheduler.reschedule_job('1', trigger=trigger)
			elif job[0] == 2:
				trigger = cron.CronTrigger(day_of_week='*/' + str(job[1]), hour='0', minute='1', second='45')
				scheduler.reschedule_job('2', trigger=trigger)
				
			elif job[0] == 3:
				if job[1] > 59:
					trigger = cron.CronTrigger(hour='*', minute='0', second='30')
					scheduler.reschedule_job('3', trigger=trigger)
				else:
					trigger = cron.CronTrigger(hour='*', minute='*/' + str(job[1]), second='30')
					scheduler.reschedule_job('3', trigger=trigger)
		for job in scheduler.get_jobs():
			logger.info("name: %s, trigger: %s, next run: %s" % (job.name, job.trigger, job.next_run_time))
			
	# Update the version name of a client
	def update_client_version(self, config, config_file, new_version, section):
		config.set(section, 'client_name', new_version)

		with open(config_file, 'w') as config_new:
			config.write(config_new)

	# Check if any clients have updated
	def multiple_update_client_version(self, config_file, logger):
		config = configparser.ConfigParser()
		config.read(config_file)

		for section in config:
			if 'Client' in section:
				new_version = client_connect.compare_client_version(config[section]['ip'], config[section]['user'],
																	config[section]['pass'],
																	config[section]['client_type'],
																	config[section]['display_name'],
																	config[section]['client_name'], logger)
				if new_version:
					self.update_client_version(config, config_file, new_version, section)
					logger.info("Updated application version of " + config[section]['display_name'])

	# Change status to 'Deleted' for deleted torrents, update directories of torrents and add missing torrents
	def update_torrent_info(self, ts_db, client_torrents, display_name, client_name, section_name, client_type, ip,
							user, pw, logger):
		conn = sqlite3.connect(ts_db)
		c = conn.cursor()
		
		c.execute("SELECT torrents.id, torrents.status, torrents.hash, torrents.directory, torrents.name FROM torrents "
				  "INNER JOIN clients ON torrents.client_id = clients.id WHERE clients.section_name=? AND "
				  "torrents.status<>'Deleted' ORDER BY torrents.hash", (section_name,))
		db_hashes = c.fetchall()

		# update torrents status

		# add the client hashes and status to a list for sorting
		client_hashes_status = []
		client_hashes = []
		client_status = []
		for torrent in client_torrents:
			client_hashes_status.append((torrent['hash'], torrent['state']))

		client_hashes_status.sort()
		# split apart so we can search the hashes
		for torrent in client_hashes_status:
			client_hashes.append(torrent[0])
			client_status.append(torrent[1])
			
		# if torrent from db not found in client hashes, change status of torrent.
		# if there is match, check for changed status, then pop to reduce array size for next search
		status_update = []
		for db_hash in db_hashes:
			search = self.index(client_hashes, db_hash[2])
			if search == None:
				status_update.append(("Deleted", db_hash[0]))
				logger.info("'" + display_name + "': '" + db_hash[4] + "' Status: " + db_hash[1] + " -> Deleted")
			else:
				if client_status[search] != db_hash[1]:
					status_update.append((client_status[search], db_hash[0]))
					logger.info("'" + display_name + "': '" + db_hash[4] + "' Status: " + db_hash[1] + " -> " +
								client_status[search])
				client_hashes.pop(search)
				client_status.pop(search)

		c.executemany("UPDATE torrents SET status=? WHERE id=?", status_update)

		# update directories of torrents, checking for any missing torrents in the process

		# add the sorted hashes to a list for searching
		existing_hashes = []
		for torrent in db_hashes:
			existing_hashes.append(torrent[2])

		directory_update = []
		name_update = []
		qbit_cookie = None
		if client_type == 'qbittorrent':
			qbit_cookie = client_connect.get_qbit_cookie(ip, user, pw, display_name, client_name, logger)

		for torrent in client_torrents:
			i = self.index(existing_hashes, torrent['hash'])
			# if the torrent isn't found in the database, it must have been missed
			if i == None:
				start_today = self.start_of_date(datetime.now())
				logger.info("'" + display_name + "': Missed torrent. Adding '" + torrent['name'] + "' to database...")
				self.add_to_db(torrent, display_name, client_name, section_name, client_type, start_today, qbit_cookie,
							   ip, c, logger)
			else:
				if torrent['downloadDir'] != db_hashes[i][3]:
					directory_update.append((torrent['downloadDir'], db_hashes[i][0]))
					logger.info("'" + display_name + "': '" + db_hashes[i][4] + "' Directory: '" +
								db_hashes[i][3] + "' -> '" + torrent['downloadDir'] + "'")
				if torrent['name'] != db_hashes[i][4]:
					name_update.append((torrent['name'], db_hashes[i][0]))
					logger.info("'" + display_name + "': '" + db_hashes[i][4] + "' renamed to '" + torrent['name'] +
								"'")

		c.executemany("UPDATE torrents SET directory=? WHERE id=?", directory_update)
		c.executemany("UPDATE torrents SET name=? WHERE id=?", name_update)
		conn.commit()
		conn.close()

	# for each client, check for deleted torrents and modified directories
	def multiple_update_info(self, ts_db, config_file, logger):
		config = configparser.ConfigParser()
		config.read(config_file)

		for section in config:
			if 'Client' in section:
				client_torrents = client_connect.get_torrents(config[section]['ip'], config[section]['user'],
															  config[section]['pass'], config[section]['client_type'],
															  config[section]['display_name'],
															  config[section]['client_name'], logger)
				if client_torrents:
					self.update_torrent_info(ts_db, client_torrents, config[section]['display_name'],
											 config[section]['client_name'], section, config[section]['client_type'],
											 config[section]['ip'], config[section]['user'], config[section]['pass'],
											 logger)

	# Backup database
	def backup_database(self, data_dir, ts_db, logger):
		logger.info("Backing up database...")
		backup_dir = os.path.join(data_dir, "backup")
		conn = sqlite3.connect(ts_db)
		backup_conn = sqlite3.connect(os.path.join(backup_dir, ("torrentstats-backup-" + str(date.today()) + ".db")))

		with backup_conn:
			conn.backup(backup_conn)
		backup_conn.close()
		conn.close()

		# keep 3 DB backups. If we have more, delete the oldest one
		files = {}
		for filename in os.scandir(backup_dir):
			files[filename.name] = os.path.getmtime(os.path.join(backup_dir, filename.name))

		if len(files) > 4:
			os.remove(os.path.join(backup_dir, min(files, key=files.get)))

		logger.info("Database backup completed")

	# check modified time of backed up files. If they're all older than 4 days, we're overdue a backup
	def check_backups(self, data_dir, ts_db, logger):
		backup_dir = os.path.join(data_dir, "backup")
		for filename in os.scandir(backup_dir):
			if os.path.getmtime(os.path.join(backup_dir, filename.name)) < (time.time() - 345600):
				self.backup_database(data_dir, ts_db, logger)
				return
		   
	# verify windows options are correct           
	def verify_win_options(self, config):
		if config['Preferences']['start_at_login'] == '1':
			win_functions.add_to_startup()
		elif config['Preferences']['start_at_login'] == '2':
			win_functions.remove_startup()
		
		if config['Preferences']['start_menu_shortcut'] == '1':
			win_functions.add_to_start_menu()
		elif config['Preferences']['start_menu_shortcut'] == '2':
			win_functions.remove_start_menu()

	# on program start, let's do a check on all frequent tasks to see if they're overdue, and execute them if needed
	def initial_start(self, data_dir, ts_db, config_file, logger):
		logger.info("Performing initial database check...")
		config = configparser.ConfigParser()
		config.read(config_file)

		conn = sqlite3.connect(ts_db)
		c = conn.cursor()
		# get all existing client names from the DB
		select_clients = c.execute("SELECT section_name FROM clients")
		clients_list = select_clients.fetchall()
		clients = []
		for client in clients_list:
			clients.append(client[0])

		# do a check on each client
		for section in config:
			if 'Client' in section:
				client_torrents = client_connect.get_torrents(config[section]['ip'], config[section]['user'],
															  config[section]['pass'], config[section]['client_type'],
															  config[section]['display_name'],
															  config[section]['client_name'], logger)
				if client_torrents:
					# if it's a new client, add it to the DB
					if section not in clients:
						self.add_client_to_db(ts_db, client_torrents, config[section]['display_name'],
											  config[section]['client_name'], section, config[section]['client_type'],
											  config[section]['ip'], config[section]['user'], config[section]['pass'],
											  logger)
					# check for activity since last run
					self.initial_check(ts_db, client_torrents, config[section]['display_name'],
									   config[section]['client_name'], section, config[section]['client_type'],
									   config[section]['ip'], config[section]['user'], config[section]['pass'], logger)
					logger.info("'" + config[section]['display_name'] + "': Updating all torrent info...")
					self.update_torrent_info(ts_db, client_torrents, config[section]['display_name'],
											 config[section]['client_name'], section, config[section]['client_type'],
											 config[section]['ip'], config[section]['user'], config[section]['pass'],
											 logger)

					new_version = client_connect.compare_client_version(config[section]['ip'], config[section]['user'],
																		config[section]['pass'],
																		config[section]['client_type'],
																		config[section]['display_name'],
																		config[section]['client_name'], logger)
					if new_version:
						self.update_client_version(config, config_file, new_version, section)
						logger.info("'" + config[section]['display_name'] + "': Updated application version")
					logger.info("Update complete")

		self.check_backups(data_dir, ts_db, logger)

		if sys.platform == "win32":
			self.verify_win_options(config)

		logger.info("Check complete")

		conn.commit()
		conn.close()
	   
	# return port number
	def get_port(self, config_file):
		config = configparser.ConfigParser()
		config.read(config_file)
		
		return config['Preferences']['port']