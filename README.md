
# BTRCP

BTRCP is a backup script that can be used to copy files and folders
facilitating the BTRFS file system as a target storage. Its main features are

* BTRFS support of the target storage device
* uses rsync to copy the actual data
* can create TAR archives instead of writing the backup to a file system
* supports SSH for remote backups

It is currently designed to run on Linux systems, where the client needs
the following commands accessible in its PATH:

* rsync
* mkdir
* stat
* ssh client

The target-machine, if BTRCP is used to backup files to a different server,
needs the following commands accessible in its path

* ssh server enabled
* rsync host enabled
* stat
* btrfs (if the corresponding strategy is used for backup)

It might also work on Windows with a Cmder or Cygwin installed. This has
to be verified.

## How to install this script

BTRCP is a python script, and needs at least Python version 3.5. It also
depends on the Python library Plumbum.

Please note that in order to install the dependecies, you need Pip 3. Please
make sure that you have Pip in version 3 installed, and that your command
actually points to version 3 in case you have multiple versions installed.
To check this, you can call

```
$> pip --version
```

To install the script dependencies, run

```
pip install plumbum
```

The BTRCP script also needs to be accessible from the current path.

## How does it work?

To use BTRCP, you just need to define the source dir(s), a destination
folder (which is possibly hosted on a different machine), and a list of
exceptions to exclude from the backup.

An example for backing up the users' home folder, and the `/etc` foder to a locally
mounted backup device. Depending on the file system used to format `/mnt/backupdev`,
BTRCP chooses between strategy 2 (using rsync in a classical way between source and
destianation) and strategy 3 (i.e. BTRCP creates subvolumes in the destination for
each timestamp when a backup is made).

```
$> btrcp.py \
    --source-dir /home \
    --source-dir /etc \
    --dest-dir /mnt/backupdev/ \
    --days-off 2 \
    --stay-on-fs
```

Another example call which backs up the whole file system starting form
its root, excluding device nodes and proc pseudo file system sub-folders.
In this example we use explicitly strategy 3, which will fail if the
destination device is not formatted with the BTRFS file system.

```
$> btrcp.py \
    --source-dir / \
    --exclude-dir /proc \
    --exclude-dir /dev \
    --exclude-dir /sys \
    --exclude-dir /run \
    --dest-dir ssh://LinuxBackupUser@192.168.1.1/volume/LinuxBackups \
    --strategy 3 \
    --days-off 2 \
    --stay-on-fs
```

## Command Line Options

`--source-dir PATH`: The path to a file or folder to backup. This parameter can be used more than once, if you whish to backup multiple folders in one go.

`--exclude-dir PATH`: A path that needs to be excluded from the backup.

`--dest-dir PATH`: The path to the (remote) location where the backup needs will be stored to.

`--hostname`: The name of the host system which is backed up. If this parameter is not specified, then the systems hostname is read and used instead.

`--strategy NUM`: The strategy that is used for the backup. Valid values are 1, 2, and 3. Default is None, in wich case a best-fit is chosen automatically. Strategy 1 creates a single TAR from all the files and folders listed as source. Strategy 2 will use rsync to perform the backup copy. Strategy 3 uses rsync as well, but needs the destination to be a BTRFS file system to make snapshots of former backups, which will create a time-line of backups.

`--days-off NUM`: sets the number of days the retention plan is offset to the current date. I.e. if days-off is set to 3, the last three days will not be touched by the retention strategy, hence will not be touched.

`--stay-on-fs`: If set, only files from the source tree which reside on the sage file system will be added to the backup.

`--preserve-path`: If set, the path from the source system will be prefixes 

`--ignore-errors`: Ignores errors and keeps on working on a backup.

`--log-file FILENAME`: Sets the log file name.

`--quiet`: No messages are printed on screen.

`--dry-run`: Performs a trial run, which causes no changes.

`--version`: Prints the version of this script to std-out.
