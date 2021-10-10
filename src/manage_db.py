import sqlite3
import os
import os.path
import time
import configparser
# import signal
import logging
import locale
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import date, datetime, timedelta
from bisect import bisect_left
# from urllib.parse import urlparse
from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.schedulers.blocking import BlockingScheduler
# from apscheduler.triggers.cron import CronTrigger
# import client_connect
from src import client_connect

t_check_frequency = 2
backup_frequency = 1
d_check_frequency = 10


class ManageDB:
	def __init__(self):
		# for windows
		# self.data_dir = "C:/Users/Cory/Documents/TorrentStatsNew"
		# for docker
		self.data_dir = "TorrentStats"

		Path(self.data_dir + "/logs").mkdir(parents=True, exist_ok=True)
		Path(self.data_dir + "/backup").mkdir(parents=True, exist_ok=True)

		self.logger = logging.getLogger('log')
		self.logger.setLevel(logging.DEBUG)

		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

		file_handler = RotatingFileHandler(self.data_dir + '/logs/log.log', maxBytes=102400, backupCount=5,
										   encoding='utf-8')
		file_handler.setFormatter(formatter)
		file_handler.setLevel(logging.DEBUG)
		self.logger.addHandler(file_handler)

		self.logger.info("Application started")

		# self.scheduler = BlockingScheduler()
		self.scheduler = BackgroundScheduler()

		config = configparser.ConfigParser()

		if os.path.isfile(self.data_dir + "/torrentstats.db") == False:
			self.first_start(self.data_dir, self.logger)
		else:
			self.initial_start(self.data_dir, self.logger)

		config.read(self.data_dir + "/config.ini")

		global t_check_frequency
		global backup_frequency
		global d_check_frequency

		t_check_frequency = config['Preferences']['torrent_check_frequency']
		backup_frequency = config['Preferences']['backup_frequency']
		d_check_frequency = config['Preferences']['deleted_check_frequency']

		if int(t_check_frequency) > 59:
			self.scheduler.add_job(self.multiple_frequent_checks, 'cron',
								   hour='*/' + str(int(int(t_check_frequency) / 60)), minute='0',
								   args=[self.data_dir, self.scheduler, self.logger], misfire_grace_time=30, id='1')
		else:
			self.scheduler.add_job(self.multiple_frequent_checks, 'cron', hour='*', minute='*/' + t_check_frequency,
								   args=[self.data_dir, self.scheduler, self.logger], misfire_grace_time=30, id='1')

		self.scheduler.add_job(self.backup_database, 'cron', day_of_week='*/' + backup_frequency, hour='0', minute='1',
							   second='45', args=[self.data_dir, self.logger], misfire_grace_time=30, id='2')

		if int(d_check_frequency) > 59:
			self.scheduler.add_job(self.multiple_update_info, 'cron', hour='*/' + str(int(int(d_check_frequency) / 60)),
								   minute='0', second='30', args=[self.data_dir, self.logger], misfire_grace_time=30,
								   id='3')
		else:
			self.scheduler.add_job(self.multiple_update_info, 'cron', hour='*', minute='*/' + d_check_frequency,
								   second='30', args=[self.data_dir, self.logger], misfire_grace_time=30, id='3')

		self.scheduler.start()

	def close_ts(self, data_dir, scheduler, logger):
		self.multiple_frequent_checks(data_dir, scheduler, logger)
		scheduler.shutdown()
		logger.info("Closing application")
		sys.exit(0)

	# Create database file and add tables
	def first_start(self, data_dir, logger):
		# create log file
		logger.info("No database exists. Creating...")

		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		c.execute("""CREATE TABLE trackers (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL
					)
					""")

		c.execute("""CREATE TABLE clients (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					section_name TEXT NOT NULL,
					display_name TEXT NOT NULL,
					client_name TEXT NOT NULL
					)
					""")

		c.execute("""CREATE TABLE torrents (
					id INTEGER PRIMARY KEY AUTOINCREMENT, 
					name TEXT NOT NULL,
					tracker_id INTEGER NOT NULL,
					client_id INTEGER NOT NULL,
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
		config['Preferences'] = {'locale': l[0],
								 'torrent_check_frequency': str(t_check_frequency),
								 'backup_frequency': str(backup_frequency),
								 'deleted_check_frequency': str(d_check_frequency)}

		with open(data_dir + "/config.ini", 'w') as config_file:
			config.write(config_file)

		logger.info("Database created and application locale set to '" + l[0] + "'")

	# add all torrents from client when client is first added
	def add_client_to_db(self, data_dir, client_torrents, display_name, client_name, section_name, client_type, ip,
						 user, pw, logger):
		logger.info("New client detected: '" + display_name + "' (" + client_name + "). Adding to DB...")

		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		# fill client table
		c.execute("INSERT INTO clients VALUES (NULL,?,?,?)", (section_name, display_name, client_name))

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

			# entry = name / tracker id / client id / status / directory / selected size / hash / hidden
			torrents_entry = (torrent['name'], tracker_id[0], client_id[0], torrent['state'], torrent['downloadDir'],
							  torrent['size'], torrent['hash'], 1)

			torrents_table.append(torrents_entry)
		c.executemany("INSERT INTO torrents VALUES (NULL,?,?,?,?,?,?,?,?)", torrents_table)

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

		select_torrent_id = c.execute("SELECT id, status FROM torrents WHERE client_id=? AND hash=?",
									  (client_id[0], torrent['hash']))
		torrent_id = select_torrent_id.fetchone()

		past_deleted = None
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

			# entry = name / tracker id / client id / status / directory / selected size / hash / hidden
			c.execute("INSERT INTO torrents VALUES (NULL,?,?,?,?,?,?,?,?)", (torrent['name'], tracker_id[0],
																			 client_id[0], torrent['state'],
																			 torrent['downloadDir'], torrent['size'],
																			 torrent['hash'], 1))

			get_torrent_id = c.execute("SELECT id, status FROM torrents WHERE client_id=? AND hash=?",
									   (client_id[0], torrent['hash']))
			torrent_id = get_torrent_id.fetchone()
		else:
			if torrent_id[1] == 'Deleted':
				past_deleted = 1
			else:
				past_deleted = 0

			# update status and size
			entry = (torrent['state'], torrent['size'], torrent_id[0])
			c.execute("UPDATE torrents SET status=?, size=? WHERE id=?", entry)

		fetch_recent = c.execute("SELECT id, total_downloaded, total_uploaded, progress FROM torrent_history WHERE "
								 "torrent_id=? AND date>=?", (torrent_id[0], start_today))
		recent = fetch_recent.fetchone()

		fetch_history = c.execute("SELECT total_downloaded, total_uploaded FROM torrent_history WHERE torrent_id=? AND "
								  "(date<? OR date IS NULL) ORDER BY id DESC LIMIT 1", (torrent_id[0], start_today))
		history = fetch_history.fetchone()

		if client_type == 'deluge':
			entry = ()
			activity_date = time.time()
			# at 00:00 check, the activity date will be logged as the next day when using time.time(). Subtract a
			# couple of minutes to correct
			if not int(datetime.fromtimestamp(activity_date).strftime('%H%M')):
				activity_date = activity_date - 180

			# if there's no historical or recent history (brand new torrent), add a new entry with latest stats
			# entry = torrents id / date / downloaded / uploaded / total downloaded / total uploaded / progress / ratio
			if not recent:
				if not history:
					entry = (torrent_id[0], activity_date, torrent['downloaded'], torrent['uploaded'],
							 torrent['downloaded'], torrent['uploaded'], torrent['progress'], torrent['ratio'])
					logger.info("'" + display_name + "': New torrent. Adding '" + torrent['name'] + "' to database")
				# if there's no recent but is a historical (first of the day), add a new entry
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					entry = (torrent_id[0], activity_date, downloaded, uploaded, torrent['downloaded'],
							 torrent['uploaded'], torrent['progress'], torrent['ratio'])
					logger.info("'" + display_name + "': New activity on existing torrent. Adding new entry to history "
													 "for '" + torrent['name'] + "'")

				c.execute("INSERT INTO torrent_history VALUES (NULL,?,?,?,?,?,?)", entry)
			# if there's historical and recent history (multiple times today of old torrent),
			# update the entry with latest stats
			else:
				recent_down = torrent['downloaded'] - recent[1]
				recent_up = torrent['uploaded'] - recent[2]

				if recent_down == 0 and recent_up == 0:
					return

				# if there is a recent but not a historical, it must be an update to a new entry from today.
				if not history:
					logger.info("'" + display_name + "': Activity on new torrent. Updating history for '" +
								torrent['name'] + "'")
					entry = (activity_date, torrent['downloaded'], torrent['uploaded'], torrent['downloaded'],
							 torrent['uploaded'], torrent['progress'], torrent['ratio'], recent[0])
				else:
					downloaded = torrent['downloaded'] - history[0]
					uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					logger.info("'" + display_name + "': Activity on existing torrent. Updating history for '" +
								torrent['name'] + "'")
					entry = (activity_date, downloaded, uploaded, torrent['downloaded'], torrent['uploaded'],
							 torrent['progress'], torrent['ratio'], recent[0])

				c.execute("UPDATE torrent_history SET date=?, downloaded=?, uploaded=?, total_downloaded=?, "
						  "total_uploaded=?, progress=?, ratio=? WHERE id=?", entry)

		else:
			if torrent['activityDate']:
				# if activityDate is 00:00, it'll get grouped as next day when pulled into tables. Subtract a couple of
				# minutes to correct
				if not int(datetime.fromtimestamp(torrent['activityDate']).strftime('%H%M')):
					torrent['activityDate'] = torrent['activityDate'] - 120

			entries = []
			# if there's no historical or recent history (brand new torrent), add a new entry with latest stats
			# entry = torrents id / date / downloaded / uploaded / total downloaded / total uploaded / progress /
			# ratio / is_new
			if not recent:
				if not history:
					if torrent['doneDate'] > 0:
						# if new torrent has completed since last launch and was completed before the last activity,
						# we'll assume the torrent was added and completed on the same date.
						# Insert an entry with full downloaded and 0 upload on completed date.
						# Add a second entry on the activity date with 0 down and full uploaded.
						if self.end_of_date(datetime.fromtimestamp(torrent['doneDate'])) < torrent['activityDate']:
							entries.append((torrent_id[0], torrent['doneDate'], torrent['downloaded'], 0,
											torrent['downloaded'], 0, torrent['progress'], torrent['ratio']))
							entries.append((torrent_id[0], torrent['activityDate'], 0, torrent['uploaded'],
											torrent['downloaded'], torrent['uploaded'], torrent['progress'],
											torrent['ratio']))
						else:
							entries.append((torrent_id[0], torrent['activityDate'], torrent['downloaded'],
											torrent['uploaded'], torrent['downloaded'], torrent['uploaded'],
											torrent['progress'], torrent['ratio']))
					# if new torrent hasn't been completed, add one entry on the activity date
					else:
						entries.append((torrent_id[0], torrent['activityDate'], torrent['downloaded'],
										torrent['uploaded'], torrent['downloaded'], torrent['uploaded'],
										torrent['progress'], torrent['ratio']))

					logger.info("'" + display_name + "': New torrent. Adding '" + torrent['name'] + "' to database")

				else:
					downloaded = None
					uploaded = None
					# compensate for re-added torrents. if status was deleted, add the previous stats to the new ones.
					if past_deleted:
						downloaded = torrent['downloaded']
						uploaded = torrent['uploaded']
					else:
						downloaded = torrent['downloaded'] - history[0]
						uploaded = torrent['uploaded'] - history[1]

					if uploaded == 0 and downloaded == 0:
						return

					# if existing torrent has completed since last launch and was completed before the last activity,
					# we'll assume the final progress of the download was completed on the done date.
					# Insert an entry with downloaded-historyDownloaded on completed date.
					# Add a second entry on the activity date with 0 down and uploaded-historyUploaded.
					if torrent['doneDate'] > 0 and torrent['downloaded'] > history[0] and not past_deleted:
						if self.end_of_date(datetime.fromtimestamp(torrent['doneDate'])) < torrent['activityDate']:
							logger.info("doneDate>0, status not deleted, downloaded>pastDownloaded,"
										" doneDate<activityDate")
							ratio_estimate = history[1] / torrent['downloaded']
							entries.append((torrent_id[0], torrent['doneDate'], downloaded, 0, torrent['downloaded'],
											history[1], torrent['progress'], ratio_estimate))
							entries.append((torrent_id[0], torrent['activityDate'], 0, uploaded, torrent['downloaded'],
											torrent['uploaded'], torrent['progress'], torrent['ratio']))
						else:
							logger.info("doneDate>0, status not deleted, downloaded>pastDownloaded,"
										" doneDate=activityDate")
							entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
											torrent['downloaded'], torrent['uploaded'], torrent['progress'],
											torrent['ratio']))

					# if re-add of old, and completed earlier than latest activity, assume all down/up was on done date
					elif torrent['doneDate'] > 0 and past_deleted:
						if self.end_of_date(datetime.fromtimestamp(torrent['doneDate'])) < torrent['activityDate']:
							logger.info("doneDate>0, status=Deleted, doneDate<activityDate")
							entries.append((torrent_id[0], torrent['doneDate'], downloaded, uploaded,
											(torrent['downloaded'] + history[0]), (torrent['uploaded'] + history[1]),
											torrent['progress'], torrent['ratio']))
						else:
							logger.info("doneDate>0, status=Deleted, doneDate=activityDate")
							entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
											(torrent['downloaded'] + history[0]), (torrent['uploaded'] + history[1]),
											torrent['progress'], torrent['ratio']))

					elif not torrent['doneDate'] and past_deleted:
						logger.info("not done, status=Deleted")
						entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
										(torrent['downloaded'] + history[0]), (torrent['uploaded'] + history[1]),
										torrent['progress'], torrent['ratio']))
					# if existing torrent hasn't been completed, add one entry on the activity date
					else:
						logger.info("not done or already completed")
						entries.append((torrent_id[0], torrent['activityDate'], downloaded, uploaded,
										torrent['downloaded'], torrent['uploaded'], torrent['progress'],
										torrent['ratio']))

					logger.info("'" + display_name + "': New activity on existing torrent. Adding new entry to history "
													 "for '" + torrent['name'] + "'")

				c.executemany("INSERT INTO torrent_history VALUES (NULL,?,?,?,?,?,?,?,?)", entries)

			# if there's historical and recent history (multiple times today of old torrent), update the entry with
			# latest stats
			else:
				if not past_deleted:
					recent_down = torrent['downloaded'] - recent[1]
					recent_up = torrent['uploaded'] - recent[2]

					progress_diff = torrent['progress'] - recent[3]
					if not progress_diff:
						if recent_down == 0 and recent_up == 0:
							return

				# if there is a recent but not a historical, it must be an update to a new entry from today.
				if not history:
					logger.info("'" + display_name + "': Activity on new torrent. Updating history for '" +
								torrent['name'] + "'")
					if not past_deleted:
						entries.append((torrent['activityDate'], torrent['downloaded'], torrent['uploaded'],
										torrent['downloaded'], torrent['uploaded'], torrent['progress'],
										torrent['ratio'], recent[0]))
					else:
						entries.append((torrent['activityDate'], torrent['downloaded'], torrent['uploaded'],
										(torrent['downloaded'] + recent[1]), (torrent['uploaded'] + recent[2]),
										torrent['progress'], torrent['ratio'], recent[0]))
				else:
					logger.info("'" + display_name + "': Activity on existing torrent. Updating history for '" +
								torrent['name'] + "'")

					downloaded = None
					uploaded = None

					if not past_deleted:
						downloaded = torrent['downloaded'] - history[0]
						uploaded = torrent['uploaded'] - history[1]

						if uploaded == 0 and downloaded == 0:
							return

						entries.append((torrent['activityDate'], downloaded, uploaded, torrent['downloaded'],
										torrent['uploaded'], torrent['progress'], torrent['ratio'], recent[0]))
					else:
						entries.append((torrent['activityDate'], (torrent['downloaded'] + recent[1]),
										(torrent['uploaded'] + recent[2]), (torrent['downloaded'] + history[0]),
										(torrent['uploaded'] + history[1]), torrent['progress'], torrent['ratio'],
										recent[0]))

				c.executemany("UPDATE torrent_history SET date=?, downloaded=?, uploaded=?, total_downloaded=?, "
							  "total_uploaded=?, progress=?, ratio=? WHERE id=?", entries)

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
	def check_deluge(self, data_dir, client_torrents):
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		recent = []
		# select most recent history of each torrent
		select_existing_torrents = c.execute("SELECT t.hash, th.total_downloaded, th.total_uploaded, MAX(th.date) FROM "
											 "torrents t INNER JOIN torrent_history th ON t.id = th.torrent_id GROUP BY"
											 " th.torrent_id ORDER BY t.hash")
		existing_torrents = select_existing_torrents.fetchall()

		# add the sorted hashes to it's own list so we can search it
		existing_hashes = []
		for torrent in existing_torrents:
			existing_hashes.append(torrent[0])

		for torrent in client_torrents:
			i = self.index(existing_hashes, torrent['hash'])
			# if the torrent is already in the DB, check for changes to down/up.
			# if it's not in the DB, it must be new so add it
			if i == None:
				recent.append(torrent)
			else:
				if torrent['downloaded'] > existing_torrents[i][1] or torrent['uploaded'] > existing_torrents[i][2]:
					recent.append(torrent)
		return recent

	# check for recent changes on program start, and add them to the DB
	def initial_check(self, data_dir, client_torrents, display_name, client_name, section_name, client_type, ip, user,
					  pw, logger):
		logger.info("Checking for recent activity from '" + display_name + "' (" + client_name + ")")
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		recent_torrents = []
		select_most_recent = c.execute("SELECT date FROM torrent_history ORDER BY date DESC LIMIT 1")
		most_recent = select_most_recent.fetchone()[0]

		current_time = datetime.now()
		if current_time.hour == 0 and current_time.minute == 0:
			current_time = current_time - timedelta(seconds=90)
		start_today = self.start_of_date(current_time)

		if client_type == 'deluge':
			recent_torrents = self.check_deluge(data_dir, client_torrents)
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
	def frequent_check(self, data_dir, client_torrents, display_name, client_name, section_name, client_type, ip, user,
					   pw, logger):
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		current_time = datetime.now()
		if current_time.hour == 0 and current_time.minute == 0:
			current_time = current_time - timedelta(seconds=90)
		start_today = self.start_of_date(current_time)

		if client_type == 'deluge':
			recent_torrents = self.check_deluge(data_dir, client_torrents)
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
	def multiple_frequent_checks(self, data_dir, scheduler, logger):
		config = configparser.ConfigParser()
		config.read(data_dir + "/config.ini")

		global t_check_frequency
		global backup_frequency
		global d_check_frequency

		# if scheduled tasks have been changed by the user, modify the jobs
		if int(t_check_frequency) != int(config['Preferences']['torrent_check_frequency']):
			logger.info("Torrent check frequency changed by user. Rescheduling job")
			if int(config['Preferences']['torrent_check_frequency']) > 59:
				scheduler.reschedule_job('1', trigger='cron', hour='*/' + str(
					int(int(config['Preferences']['torrent_check_frequency']) / 60)), minute='0')
			else:
				scheduler.reschedule_job('1', trigger='cron', hour='*', minute='*/' +
										 config['Preferences']['torrent_check_frequency'])
			t_check_frequency = config['Preferences']['torrent_check_frequency']

		if int(backup_frequency) != int(config['Preferences']['backup_frequency']):
			logger.info("Backup frequency changed by user. Rescheduling job")
			scheduler.reschedule_job('2', trigger='cron', day_of_week='*/' + backup_frequency, hour='0', minute='1',
									 second='45')
			backup_frequency = config['Preferences']['backup_frequency']

		if int(d_check_frequency) != int(config['Preferences']['deleted_check_frequency']):
			logger.info("Frequency of checking for deleted torrents changed by user. Rescheduling job")
			if int(config['Preferences']['deleted_check_frequency']) > 59:
				scheduler.reschedule_job('3', trigger='cron', hour='*/' + str(
					int(int(config['Preferences']['deleted_check_frequency']) / 60)), minute='0', second='30')
			else:
				scheduler.reschedule_job('3', trigger='cron', hour='*', minute='*/' +
										 config['Preferences']['deleted_check_frequency'], second='30')
			d_check_frequency = config['Preferences']['deleted_check_frequency']

		# get all existing client names from the DB
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
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
						self.add_client_to_db(data_dir, client_torrents, config[section]['display_name'],
											  config[section]['client_name'], section, config[section]['client_type'],
											  config[section]['ip'], config[section]['user'], config[section]['pass'],
											  logger)
					self.frequent_check(data_dir, client_torrents, config[section]['display_name'],
										config[section]['client_name'], section, config[section]['client_type'],
										config[section]['ip'], config[section]['user'], config[section]['pass'], logger)

		conn.commit()
		conn.close()

	# Update the version name of the client in config and the db
	def update_client_version(self, data_dir, new_version, section):
		config = configparser.ConfigParser()
		config.read(data_dir + "/config.ini")
		config.set(section, 'client_name', new_version)

		with open(data_dir + "/config.ini", 'w') as config_file:
			config.write(config_file)

		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()
		c.execute("UPDATE clients SET client_name=? WHERE section_name=?", (new_version, section))
		conn.commit()
		conn.close()

	# Change status to 'Deleted' for deleted torrents, update directories of torrents and add missing torrents
	def update_torrent_info(self, data_dir, client_torrents, display_name, client_name, section_name, client_type, ip,
							user, pw, logger):
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		c = conn.cursor()

		c.execute("SELECT torrents.id, torrents.hash, torrents.directory, torrents.name FROM torrents INNER JOIN "
				  "clients ON torrents.client_id = clients.id WHERE clients.section_name=? AND "
				  "torrents.status<>'Deleted' ORDER BY torrents.hash", (section_name,))
		db_hashes = c.fetchall()

		# update status for deleted torrents

		# add the client hashes to a list for sorting and then searching
		client_hashes = []
		for torrent in client_torrents:
			client_hashes.append(torrent['hash'])

		client_hashes.sort()

		# if torrent from db not found in client hashes, change status of torrent.
		# if there is match, pop to reduce array size for next search
		status_update = []
		for db_hash in db_hashes:
			search = self.index(client_hashes, db_hash[1])
			if search == None:
				status_update.append((db_hash[0],))
				logger.info("'" + display_name + "': '" + db_hash[3] + "' no longer in directory. Status changed to "
																	   "'Deleted'")
			else:
				client_hashes.pop(search)

		c.executemany("UPDATE torrents SET status='Deleted' WHERE id=?", status_update)

		# update directories of torrents, checking for any missing torrents in the process

		# add the sorted hashes to a list for searching
		existing_hashes = []
		for torrent in db_hashes:
			existing_hashes.append(torrent[1])

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
				if torrent['downloadDir'] != db_hashes[i][2]:
					directory_update.append((torrent['downloadDir'], db_hashes[i][0]))
					logger.info("'" + display_name + "': Directory of '" + db_hashes[i][3] + "' has changed. Updating "
																							 "database")
				if torrent['name'] != db_hashes[i][3]:
					name_update.append((torrent['name'], db_hashes[i][0]))
					logger.info("'" + display_name + "': Name of '" + db_hashes[i][3] + "' has changed. Updating "
																						"database")

		c.executemany("UPDATE torrents SET directory=? WHERE id=?", directory_update)
		c.executemany("UPDATE torrents SET name=? WHERE id=?", name_update)
		conn.commit()
		conn.close()

	# for each client, update the client version name and check for deleted torrents and modified directories
	def multiple_update_info(self, data_dir, logger):
		logger.info("Updating client and torrent info...")

		config = configparser.ConfigParser()
		config.read(data_dir + "/config.ini")

		for section in config:
			if 'Client' in section:
				new_version = client_connect.compare_client_version(config[section]['ip'], config[section]['user'],
																	config[section]['pass'],
																	config[section]['client_type'],
																	config[section]['display_name'],
																	config[section]['client_name'], logger)
				if new_version:
					logger.info("Application version of '" + config[section]['display_name'] + "' has changed. "
																							   "Updating")
					self.update_client_version(data_dir, new_version, section)
				client_torrents = client_connect.get_torrents(config[section]['ip'], config[section]['user'],
															  config[section]['pass'], config[section]['client_type'],
															  config[section]['display_name'],
															  config[section]['client_name'], logger)
				if client_torrents:
					self.update_torrent_info(data_dir, client_torrents, config[section]['display_name'],
											 config[section]['client_name'], section, config[section]['client_type'],
											 config[section]['ip'], config[section]['user'], config[section]['pass'],
											 logger)

		logger.info("Update complete")

	# Backup database
	def backup_database(self, data_dir, logger):
		logger.info("Backing up database...")
		conn = sqlite3.connect(data_dir + "/torrentstats.db")
		backup_conn = sqlite3.connect(data_dir + "/backup/torrentstats-backup-" + str(date.today()) + ".db")

		with backup_conn:
			conn.backup(backup_conn)
		backup_conn.close()
		conn.close()

		# keep 3 DB backups. If we have more, delete the oldest one
		files = {}
		for filename in os.scandir(data_dir + "/backup"):
			files[filename.name] = os.path.getmtime(data_dir + "/backup/" + filename.name)

		if len(files) > 4:
			os.remove(data_dir + "/backup/" + min(files, key=files.get))

		logger.info("Database backup completed")

	# check modified time of backed up files. If they're all older than 4 days, we're overdue a backup
	def check_backups(self, data_dir, logger):
		for filename in os.scandir(data_dir + "/backup"):
			if os.path.getmtime(data_dir + "/backup/" + filename.name) < (time.time() - 345600):
				self.backup_database(data_dir, logger)
				return

	# on program start, let's do a check on all frequent tasks to see if they're overdue, and execute them if needed
	def initial_start(self, data_dir, logger):
		logger.info("Performing initial database check...")

		config = configparser.ConfigParser()
		config.read(data_dir + "/config.ini")

		conn = sqlite3.connect(data_dir + "/torrentstats.db")
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
						self.add_client_to_db(data_dir, client_torrents, config[section]['display_name'],
											  config[section]['client_name'], section, config[section]['client_type'],
											  config[section]['ip'], config[section]['user'], config[section]['pass'],
											  logger)
					# check for activity since last run
					self.initial_check(data_dir, client_torrents, config[section]['display_name'],
									   config[section]['client_name'], section, config[section]['client_type'],
									   config[section]['ip'], config[section]['user'], config[section]['pass'], logger)
					logger.info("Updating client and torrent info of '" + config[section]['display_name'] + "'...")
					self.update_torrent_info(data_dir, client_torrents, config[section]['display_name'],
											 config[section]['client_name'], section, config[section]['client_type'],
											 config[section]['ip'], config[section]['user'], config[section]['pass'],
											 logger)
					logger.info("Update complete")

		self.check_backups(data_dir, logger)
		logger.info("Check complete")

		conn.commit()
		conn.close()