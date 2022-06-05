
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

`--source-dir PATH`: The path to a file or folder to backup. This parameter can be used more than once, if you whish to backup multiple folders in one go.

`--exclude-dir PATH`: A path that needs to be excluded from the backup.

`--dest-dir PATH`: The path to the (remote) location where the backup needs will be stored to.

`--hostname`: The name of the host system which is backed up. If this parameter is not specified, then the systems hostname is read and used instead.

`--strategy NUM`: The strategy that is used for the backup. Valid values are 1, 2, and 3. Default is 2. Strategy 1 creates a single TAR from all the files and folders listed as source. Strategy 2 will use rsync to perform the backup copy. Strategy 3 uses rsync as well, but needs the destination to be a BTRFS file system to make snapshots of former backups, which will create a time-line of backups.

`--days-off NUM`: sets the number of days the retention plan is offset to the current date. I.e. if days-off is set to 3, the last three days will not be touched by the retention strategy, hence will not be touched.

`--stay-on-fs`: If set, only files from the source tree which reside on the sage file system will be added to the backup.

`--ignore-errors`: Ignores errors and keeps on working on a backup.

`--log-file FILENAME`: Sets the log file name.

`--quiet`: No messages are printed on screen.

`--dry-run`: Performs a dry-run.

`--version`: Prints the version of this script to std-out.
