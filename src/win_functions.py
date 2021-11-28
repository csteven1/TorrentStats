import win32com, win32com.client
import pythoncom
import getpass
import os, os.path
import sys
from pathlib import Path


# create batch file in startup folder
def add_to_startup():
	user_name = getpass.getuser()
	exe_path = os.path.join(os.path.dirname(sys.executable), "torrentstats.exe")
	bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % user_name

	try:
		with open(bat_path + '\\' + "startTorrentStats.bat", "r") as bat_file:
			split_str = bat_file.read().split()
			if split_str[-1] == exe_path:
				return
		# if the destination is wrong, write a new batch file
		with open(bat_path + '\\' + "startTorrentStats.bat", "w") as bat_file:
			bat_file.write(r'start "" ' + exe_path)
	# if there is no file, write one
	except FileNotFoundError:
		with open(bat_path + '\\' + "startTorrentStats.bat", "w") as bat_file:
		  bat_file.write(r'start "" ' + exe_path)


def remove_startup():
	user_name = getpass.getuser()
	startup_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % user_name
	bat_path = Path(startup_path).joinpath("startTorrentStats.bat")
	bat_path.unlink(missing_ok=True)
	

# create shortcut to exe in start menu folder
def add_to_start_menu():
	user_name = getpass.getuser()
	exe_path = os.path.join(os.path.dirname(sys.executable), "torrentstats.exe")
	dest_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\TorrentStats.lnk' % user_name

	pythoncom.CoInitialize()
	shell = win32com.client.Dispatch("WScript.Shell")
	shortcut = shell.CreateShortCut(dest_path)
	
	if os.path.isfile(dest_path):
		if os.path.isfile(shortcut.Targetpath):
			if shortcut.Targetpath == exe_path:
				return
	shortcut.IconLocation = exe_path
	shortcut.Targetpath = exe_path
	shortcut.save()


# remove shortcut from start menu folder
def remove_start_menu():
	user_name = getpass.getuser()
	start_folder = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs' % user_name
	shortcut = Path(start_folder).joinpath("TorrentStats.lnk")
	shortcut.unlink(missing_ok=True)
