# fs-poll-watch-touch

In an attempt to have development env replicate prod, creating dev env as VM guest on a desktop. But still want to use rich desktop IDE. Solution - keep source dir tree on desktop but NFS share it on dev vm for runtime. But issue here - nfs shares do not fire inotify events which sometimes needed for things like triggering builds, UI hot reloads, etc.

Ugly but working solution for small directory trees seems to be watching files on guest vm for changes by polling and touching files on VM share triggering inotify events.

    python poll_watch_and_touch.py <dir root to watch> <poll timeout sec>.

For Example to poll your AwesomeProject share on a guest VM every 4 seconds:

    python poll_watch_and_touch.py /home/vagrant/AwesomeProject 4
