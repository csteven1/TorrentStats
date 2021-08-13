from multiprocessing import cpu_count
from src import manage_db

def on_starting(server):
	global o
	o = manage_db.ManageDB()
	
def on_exit(server):
	o.close_ts(o.data_dir, o.scheduler, o.logger)
	
def max_workers():
	return 2*cpu_count()+1
	
preload_app = True
workers = max_workers()