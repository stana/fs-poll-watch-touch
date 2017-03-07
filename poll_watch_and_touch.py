"""
VM shares (nfs) do not fire inotify events breaking file watching tools
relied upon during development to trigger events like project builds, 
hot reloads, etc.

Ugly but working solution for small directory trees seems to be 
watching files for changes by polling and touching files on VM 
share triggering inotify events.

    python poll_watch_and_touch.py <dir root to watch> <poll timeout sec>.

For Example to poll your AwesomeProject share on a guest VM every 4 seconds:

    python poll_watch_and_touch.py /home/vagrant/AwesomeProject 4

"""
import sys
import os
import time
import logging
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler 


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('poll_watch_and_touch')


def _retouch_file(file_path, time_stamp=None):
    logger.debug("Re-touching file - {}".format(file_path))
    if not time_stamp:
        # just get file modified time or time now
        mod_time = os.path.getmtime(file_path) or time.time()
        time_stamp = (mod_time, mod_time) 
    with open(file_path, 'a'):
        os.utime(file_path, time_stamp)


def _touch_parent_dir(file_path):
    # go up parent dir getting first existing parent path
    dir_path = os.path.dirname(file_path)
    for i in range(0, len(file_path.split('/'))):
        if os.path.exists(dir_path):
            break
        dir_path = os.path.dirname(dir_path)

    if dir_path and len(dir_path) > 1:
        logger.debug("Touching dir - {}".format(dir_path))
        # we have dir path and not '/'
        tmp_file = dir_path + '/{}'.format(time.time())
        #print 'touching dir by creating tmp_file ' + tmp_file 
        open(tmp_file, 'w').close()
        os.remove(tmp_file) 


class PollingTouchFileHandler(FileSystemEventHandler):
    """
    For some reason file modified over NFS triggers 
    always on_created AND on_modified events using
    Polling observer. So only only need on_created. 
    """
    def on_created(self, event):
        if os.path.isfile(event.src_path):
            logger.debug("File created event, src - {}".format(event.src_path))
            _retouch_file(event.src_path) 

    def on_deleted(self, event):
        logger.debug("Deleted event, src - {}".format(event.src_path))
        _touch_parent_dir(event.src_path)

    def on_moved(self, event):
        logger.debug("Moved event, source - {}, dest - {}".format(event.src_path, event.dest_path))
        if os.path.isfile(event.dest_path):
            _retouch_file(event.dest_path)
        else: 
            _touch_parent_dir(event.dest_path)
        if os.path.dirname(event.src_path) != os.path.dirname(event.dest_path):
            _touch_parent_dir(event.src_path)

    # file modifications on VM share (nfs) always triggering create event
    # so don't need modified event
    #def on_modified(self, event):
    #    if os.path.isfile(event.src_path):
    #        print "modified, touching {}".format(event.src_path)
    #        _retouch_file(event.src_path) 


if __name__ == "__main__":
    
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    # default polling_timeout to 3 seconds
    polling_timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    logger.info('Starting watching and touching - path - {}, polling timeout - {} ...'.format(path, polling_timeout))

    event_handler = PollingTouchFileHandler()
    #observer = Observer()
    observer = PollingObserver(timeout=polling_timeout)
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
