
# BTRCP

BTRCP is a backup-command that can be used to copy files and folders
facilitating the BTRFS as its target storage. Its main features are

* BTRFS support of the target storage device
* uses rsync to copy the actual data
* can create TAR archives instead of writing the backup to a file system
* supports SSH for remote backups

## How to install this script

BTRCP is a python script, and needs at least Python version 3.5. It also
depends on the Python library Plumbum. To install the script dependencies,
run

```
pip install plumbum
```

The BTRCP script also needs to be accessible from the current path.

## How does it work?

To use BTRCP, you just need to define the source dir(s), a destination
folder (which is possibly hosted on a different machine), and a list of
exceptions to exclude from the backup.

An example call might look like this

```
btrcp.py --source-dir / --exclude-dir /proc --exclude-dir /dev --exclude-dir /sys --exclude-dir /run --dest-dir ssh://LinuxBackupUser@192.168.10.241/volume1/LinuxBackups --strategy 3 --days-off 2 --stay-on-fs
```

## Command Line Options

