import xmlrpc.client
import xmlrpc
import requests
import json
from urllib.parse import urlparse
from requests.exceptions import Timeout, HTTPError, ConnectionError


def get_transmission_status(status_code):
	if status_code == 0:
		return 'Paused'
	elif status_code == 3:
		return 'Queued'
	elif status_code == 4:
		return 'Downloading'
	elif status_code == 6:
		return 'Seeding'
	else:
		return 'Unknown'


def get_qbit_status(status):
	if 'paused' in status:
		return 'Paused'
	elif 'DL' in status or status == 'downloading':
		return 'Downloading'
	elif 'UP' in status or status == 'uploading':
		return 'Seeding'
	else:
		return 'Unknown'


# login to qbit and return cookie
def get_qbit_cookie(ip, user, pw, display_name, client_name, logger):
	try:
		auth = {'username': user, 'password': pw}
		request_cookie = requests.post(ip + '/api/v2/auth/login', data=auth, timeout=0.5)

		if request_cookie.status_code == 200 or request_cookie.status_code == 403:
			if request_cookie.cookies:
				return {'SID': request_cookie.cookies['SID']}
			else:
				logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). Please "
							 "ensure the username and password are correct.")
		else:
			request_cookie.raise_for_status()
	except:
		logger.error("Connection to '" + display_name + "' (" + client_name + ") failed. Please ensure the client is "
					 "running.")


# get tracker for a qBittorrent torrent
def get_qbit_tracker(torrent_hash, cookie, ip, display_name, client_name, logger):
	try:
		get_tracker_q = requests.get(ip + '/api/v2/torrents/trackers?hash=' + torrent_hash, cookies=cookie, timeout=0.5)
		if get_tracker_q.status_code == 200 or get_tracker_q.status_code == 403:
			t = get_tracker_q.json()
			return urlparse(t[3]['url']).hostname
		else:
			get_tracker_q.raise_for_status()
	except:
		logger.error("Connection to '" + display_name + "' (" + client_name + ") failed. Please ensure the client is "
					 "running.")


# get all torrents from client, normalize key names, trim unnecessary fields and return
def get_torrents(ip, user, pw, client, display_name, client_name, logger):
	if client == "transmission":
		try:
			transmission_session_id = None
			auth = (user, pw)
			method = 'torrent-get'
			fields = ["name", "downloadedEver", "uploadedEver", "activityDate", "doneDate", "addedDate", "percentDone",
					  "sizeWhenDone", "downloadDir", "trackerStats", "uploadRatio", "status", "hashString"]
			field_dict = {'fields': fields}
			body = json.dumps({
				'method': method,
				'arguments': field_dict
			})

			for x in range(2):
				headers = {'X-Transmission-Session-Id': transmission_session_id}
				resp = requests.post(ip + '/transmission/rpc/', body, headers=headers, auth=auth, timeout=0.5)
				if resp.status_code == 409:
					transmission_session_id = resp.headers['X-Transmission-Session-Id']
				elif resp.status_code == 200:
					all_torrents = resp.json()
					for torrent in all_torrents['arguments']['torrents']:
						torrent['downloaded'] = torrent.pop('downloadedEver')
						torrent['uploaded'] = torrent.pop('uploadedEver')
						if not torrent['activityDate']:
							torrent['activityDate'] = torrent['addedDate']
							torrent['ratio'] = 0
							torrent.pop('uploadRatio')
						else:
							torrent['ratio'] = torrent.pop('uploadRatio')
						torrent['progress'] = torrent.pop('percentDone')
						torrent['size'] = torrent.pop('sizeWhenDone')
						tracker_name = urlparse(torrent['trackerStats'][0]['host']).hostname
						torrent['tracker'] = tracker_name
						torrent.pop('trackerStats')
						torrent['state'] = get_transmission_status(torrent['status'])
						torrent.pop('status')
						torrent['hash'] = torrent.pop('hashString')

					return all_torrents['arguments']['torrents']
				elif resp.status_code == 401:
					logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). "
								 "Please ensure the username and password are correct.")
				else:
					raise (resp.raise_for_status())

		except:
			return

	elif client == "qbittorrent":
		try:
			auth = {'username': user, 'password': pw}
			fetch_qbit_cookie = requests.post(ip + '/api/v2/auth/login', data=auth, timeout=0.5)

			if fetch_qbit_cookie.status_code == 200 or fetch_qbit_cookie.status_code == 403:
				if fetch_qbit_cookie.cookies:
					qbit_cookie = {'SID': fetch_qbit_cookie.cookies['SID']}

					get_all_torrents = requests.post(ip + '/api/v2/torrents/info', cookies=qbit_cookie,
													 timeout=0.5)
					all_torrents = get_all_torrents.json()
					for torrent in all_torrents:
						if not torrent['last_activity']:
							torrent['activityDate'] = torrent['added_on']
							torrent.pop('last_activity')
						else:
							torrent['activityDate'] = torrent.pop('last_activity')
						torrent['addedDate'] = torrent.pop('added_on')
						torrent['doneDate'] = torrent.pop('completion_on')
						torrent['downloadDir'] = torrent.pop('save_path')
						torrent['state'] = get_qbit_status(torrent['state'])
						for unused_field in ['amount_left', 'auto_tmm', 'availability', 'category', 'completed',
											 'dl_limit', 'dlspeed', 'downloaded_session', 'eta', 'f_l_piece_prio',
											 'force_start', 'magnet_uri', 'max_ratio','max_seeding_time',
											 'num_complete', 'num_incomplete', 'num_leechs', 'num_seeds', 'priority',
											 'ratio_limit', 'seeding_time_limit', 'seen_complete', 'seq_dl',
											 'super_seeding', 'tags', 'time_active', 'total_size', 'tracker',
											 'up_limit', 'uploaded_session', 'upspeed', 'content_path', 'seeding_time',
											 'trackers_count']:
							torrent.pop(unused_field)

					return all_torrents
				else:
					logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). "
								 "Please ensure the username and password are correct.")
			else:
				fetch_qbit_cookie.raise_for_status()
		except:
			return

	elif client == "deluge":
		try:
			# open session and login
			with requests.Session() as s:
				header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
				login_data = '{"method": "auth.login", "params": ["' + pw + '"], "id": 1}'
				login_deluge = s.post(ip + '/json', data=login_data, headers=header, timeout=0.5)

				if login_deluge.status_code == 200:
					confirm = login_deluge.json()
					if not confirm['result']:
						logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). "
									 "Please ensure the username and password are correct.")
					else:
						# get torrents
						torrents_data = ('{"method": "core.get_torrents_status", "params": [[],["name", "hash", "state"'
										 ', "progress", "time_added", "download_location", "total_wanted", '
										 '"all_time_download", "total_uploaded", "ratio", "tracker_host"]], "id": 1}')
						resp = s.post(ip + '/json', data=torrents_data, headers=header, timeout=0.5)

						torrents = resp.json()
						all_torrents = []
						if torrents['result']:
							for torrent in torrents['result']:
								torrents['result'][torrent]['downloaded'] = torrents['result'][torrent].pop(
									'all_time_download')
								torrents['result'][torrent]['uploaded'] = torrents['result'][torrent].pop(
									'total_uploaded')
								torrents['result'][torrent]['size'] = torrents['result'][torrent].pop('total_wanted')
								torrents['result'][torrent]['progress'] = torrents['result'][torrent]['progress'] / 100
								torrents['result'][torrent]['addedDate'] = torrents['result'][torrent]['time_added']
								torrents['result'][torrent]['downloadDir'] = torrents['result'][torrent].pop(
									'download_location')
								if torrents['result'][torrent]['ratio'] < 0:
									torrents['result'][torrent]['ratio'] = 0
								torrents['result'][torrent]['tracker'] = torrents['result'][torrent].pop('tracker_host')
								all_torrents.append(torrents['result'][torrent])

						return all_torrents
				else:
					login_deluge.raise_for_status()

		except:
			return
			
	elif client == "rtorrent":
		try:
			server = xmlrpc.client.ServerProxy(ip)
			torrents = server.d.multicall2("", "main", "d.name=", "d.bytes_done=", "d.up.total=", 
										   "d.timestamp.finished=", "d.load_date=", "d.size_bytes=", "d.directory=", 
										   "d.ratio=", "d.state=", "d.hash=")
			all_torrents = []
			if torrents:
				for torrent in torrents:
					trackers = server.t.multicall(torrent[9], "t.id=", "t.url=")
					tracker = urlparse(trackers[0][0]).hostname
					state = ""
					if torrent[3] and torrent[8]:
						state = "Seeding"
					elif not torrent[3] and torrent[8]:
						state = "Downloading"
					else:
						state = "Paused"
					progress = 1
					if not torrent[3]:
						progress = round(torrent[1] / torrent[5], 4)
					all_torrents.append({'name': torrent[0], 'downloaded': torrent[1], 'uploaded': torrent[2], 
											  'doneDate': torrent[3], 'addedDate': torrent[4], 'progress': progress,
											  'size': torrent[5], 'downloadDir': torrent[6], 'tracker': tracker, 
											  'ratio': torrent[7], 'state': state, 'hash': torrent[9]})
				return all_torrents
		
		except xmlrpc.client.ProtocolError:
			logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). Please "
						 "ensure the username and password are correct.")
		except:
			return


# attempt to connect to the client
def test_client(ip, user, pw, client):
	if client == "transmission":
		try:
			auth = (user, pw)
			test_transmission = requests.get(ip + '/transmission/rpc/', auth=auth, timeout=0.5)
			
			if test_transmission.status_code == 409 or test_transmission.status_code == 200:
				if test_transmission.headers['X-Transmission-Session-Id']:
					return 0
				else:
					return 'err_no_resp'
			elif test_transmission.status_code == 401:
				return 'err_trans_auth'
			else:
				return 'err_no_resp'
		except:
			return 'err_no_resp'

	elif client == "qbittorrent":
		try:
			auth = {'username': user, 'password': pw}
			fetch_qbit_cookie = requests.post(ip + '/api/v2/auth/login', data=auth, timeout=0.5)

			if fetch_qbit_cookie.status_code == 200 or fetch_qbit_cookie.status_code == 403:
				if fetch_qbit_cookie.cookies:
					return 0
				else:
					return 'err_no_resp'
			else:
				fetch_qbit_cookie.raise_for_status()
		except:
			return 'err_no_resp'

	elif client == "deluge":
		try:
			# open session and login
			with requests.Session() as s:
				header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
				login_data = '{"method": "auth.login", "params": ["' + pw + '"], "id": 1}'
				login_deluge = s.post(ip + '/json', data=login_data, headers=header, timeout=0.5)

				if login_deluge.status_code == 200:
					confirm = login_deluge.json()
					if not confirm['result']:
						return 'err_del_auth'
					else:
						# get deluge version
						version_data = '{"method": "daemon.get_version", "params": [], "id": 1}'
						resp = s.post(ip + '/json', data=version_data, headers=header, timeout=0.5)

						return 0
				else:
					login_deluge.raise_for_status()

		except:
			return 'err_no_resp'
	
	elif client == "rtorrent":
		try:
			server = xmlrpc.client.ServerProxy(ip)
			version = server.system.client_version()
			
			return 0
		except xmlrpc.client.ProtocolError:
			return "err_rtor_auth"
		except:
			return 'err_no_resp'


# attempt to identify the client using the ip and auth given by the user
# if successful, return the version
def identify_client(ip_orig, user, pw, client_ips, logger):
	ip = ip_orig
	mod_ip = ('', 'http://','https://')

	for test_ip in range(3):
		ip = ip_orig
		ip = mod_ip[test_ip]+ip
		
		# return error if IP matches any existing IP
		for client_ip in client_ips:
			if client_ip == ip:
				return "err_ip_exist"

		try:
			# try transmission
			try:
				auth = (user, pw)
				body = json.dumps({'method': 'session-get'})
				transmission_session_id = None
				trans_resp = None

				for x in range(2):
					headers = {'X-Transmission-Session-Id': transmission_session_id}
					resp = requests.post(ip + '/transmission/rpc/', body, headers=headers, auth=auth, timeout=0.5)
					
					if resp.status_code == 409:
						transmission_session_id = resp.headers['X-Transmission-Session-Id']
					elif resp.status_code == 200:
						trans_resp = resp.json()
						break
					elif resp.headers['Server'] == 'Transmission' and resp.status_code == 401:
						return "err_trans_auth"
					else:
						raise (resp.raise_for_status())

				return (ip, "transmission", "Transmission " + trans_resp['arguments']['version'])

			except:
				# try qbittorrent
				try:
					auth = {'username': user, 'password': pw}
					test_qbittorrent = requests.post(ip + '/api/v2/auth/login', data=auth, timeout=0.5)
					
					# 503 text related to rtorrent. raise to proceed to rtorrent
					if '503' in test_qbittorrent.text:
						raise

					if test_qbittorrent.status_code == 200 or test_qbittorrent.status_code == 403:
						if test_qbittorrent.cookies:
							qbit_cookie = {'SID': test_qbittorrent.cookies['SID']}
							qbit_version = requests.post(ip + '/api/v2/app/version', cookies=qbit_cookie, timeout=0.5)

							return (ip, "qbittorrent", "qBittorrent " + qbit_version.text)
						else:
							return "err_qbit_auth"
					else:
						test_qbittorrent.raise_for_status()

				except:
					# try deluge
					try:
						# open session and login
						with requests.Session() as s:
							header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
							login_data = '{"method": "auth.login", "params": ["' + str(pw) + '"], "id": 1}'
							test_deluge = s.post(ip + '/json', data=login_data, headers=header, timeout=0.5)

							if test_deluge.status_code == 200:
								confirm = test_deluge.json()
								if not confirm['result']:
									return "err_del_auth"
								else:
									# get deluge version
									version_data = '{"method": "daemon.get_version", "params": [], "id": 1}'
									resp = s.post(ip + '/json', data=version_data, headers=header, timeout=0.5)
									deluge_version = resp.json()
									if deluge_version['result']:
										return (ip, "deluge", "Deluge " + deluge_version['result'])
									else:
										return "err_del_auth"
							else:
								test_deluge.raise_for_status()

					except:
						# try rtorrent
						if user:
							parsed = urlparse(ip)
							ip = parsed._replace(netloc=user + ":" + pw + "@" + parsed.netloc).geturl()
							
						server = xmlrpc.client.ServerProxy(ip)
						version = server.system.client_version()
						
						return (ip, "rtorrent", "rTorrent " + version)
							
		except xmlrpc.client.ProtocolError:
			return "err_rtor_auth"
		except:
			pass
	return "err_no_resp"


# compare app version name from config. if different, return new one
def compare_client_version(ip, user, pw, client, display_name, client_name, logger):
	failed_error = "Connection to '" + display_name + "' (" + client_name + ") failed. Please ensure the client is " \
				   "running."

	if client == 'transmission':
		try:
			auth = (user, pw)
			body = json.dumps({'method': 'session-get'})
			transmission_session_id = None
			trans_resp = None

			for x in range(2):
				headers = {'X-Transmission-Session-Id': transmission_session_id}
				resp = requests.post(ip + '/transmission/rpc/', body, headers=headers, auth=auth, timeout=0.5)
				if resp.status_code == 409:
					transmission_session_id = resp.headers['X-Transmission-Session-Id']
				elif resp.status_code == 200:
					trans_resp = resp.json()
					break
				else:
					raise (resp.raise_for_status())
			version = "Transmission " + trans_resp['arguments']['version']

			if version != client_name:
				return version
			else:
				return None
		except:
			logger.error(failed_error)

	elif client == 'qbittorrent':
		try:
			auth = {'username': user, 'password': pw}
			fetch_qbit_cookie = requests.post(ip + '/api/v2/auth/login', data=auth, timeout=0.5)

			if fetch_qbit_cookie.status_code == 200 or fetch_qbit_cookie.status_code == 403:
				if fetch_qbit_cookie.cookies:
					qbit_cookie = {'SID': fetch_qbit_cookie.cookies['SID']}

					qbit_version = requests.post(ip + '/api/v2/app/version', cookies=qbit_cookie, timeout=0.5)
					version = "qBittorrent " + qbit_version.text

					if version != client_name:
						return version
					else:
						return None
				else:
					logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). "
								 "Please ensure the username and password are correct.")
			else:
				fetch_qbit_cookie.raise_for_status()
		except:
			logger.error(failed_error)

	elif client == 'deluge':
		try:
			# open session and login
			with requests.Session() as s:
				header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
				login_data = '{"method": "auth.login", "params": ["' + pw + '"], "id": 1}'
				login_deluge = s.post(ip + '/json', data=login_data, headers=header, timeout=0.5)

				if login_deluge.status_code == 200:
					confirm = login_deluge.json()
					if not confirm['result']:
						logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). "
									 "Please ensure the username and password are correct.")
					else:
						# get deluge version
						version_data = '{"method": "daemon.get_version", "params": [], "id": 1}'
						resp = s.post(ip + '/json', data=version_data, headers=header, timeout=0.5)
						deluge_version = resp.json()
						if deluge_version['result']:
							version = "Deluge " + deluge_version['result']
							if version != client_name:
								return version
						return None
				else:
					login_deluge.raise_for_status()

		except:
			logger.error(failed_error)
						 
	elif client == 'rtorrent':
		try:
			server = xmlrpc.client.ServerProxy(ip)
			version = "rTorrent " + server.system.client_version()
			
			if version != client_name:
				return version
			else:
				return None
		
		except xmlrpc.client.ProtocolError:
			logger.error("Authentication error connecting to '" + display_name + "' (" + client_name + "). Please "
						 "ensure the username and password are correct.")
		except:
			logger.error(failed_error)