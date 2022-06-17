
# BTRCP

BTRCP is a backup script that can be used to copy files and folders
facilitating the BTRFS file system as a target storage. Its main features are

* facilitates BTRFS on the target storage device by creating snapshots for each backup. This is well suited for hourly backups.
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

## Before We Start: The Installation

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

## Quickstart

To backup your files, you preferrably have a disk at hand which is formatted
with the BTRFS file system. Note that this script will also work on devices
which are not in BTRFS format, but to gain the most out of this script, you
might want to look into using BTRFS as a target for your backups.

A quick start might be to back up your most important data, which should reside
in your home directory. To backup all home directories just call

```
$> btrcp.py \
    --source /home \
    --source /etc \
    --dest-dir /mnt/backup-device/ \
    --stay-on-fs
```

In this example we assumed that the backup device is mounted under `/mnt/backup-device`.
We've also included the `/etc` folder as this is the place where some system
applications store their configuration.

In case we want to push the backup to a server offering rsync over SSH, the
example from above changes to

```
$> btrcp.py \
    --source /home \
    --source /etc \
    --dest-dir ssh://BackupUserName@192.168.1.2/path/on/the/server \
    --stay-on-fs
```

Here we also assumed that the IP of the server is `192.168.1.2`, the user which
has access to the server via SSH has the name `BackupUserName`, and the path
on the server to the location we want to put the backup is `/path/on/the/server`.

## Command Line Options

`--source PATH`: The path to a file or folder to backup. This parameter can be used more than once, if you whish to backup multiple folders in one go.

`--exclude PATH`: A path that needs to be excluded from the backup.

`--dest-dir PATH`: The path to the (remote) location where the backup needs will be stored to.

`--hostname`: The name of the host system which is backed up. If this parameter is not specified, then the systems hostname is read and used instead. The hostname is important for backup strategy 2 and 3 which creates a folder on the target device labeled with the hostname's name. This enables the user to backup multiple machines to the same target.

`--strategy NUM`: The strategy that is used for the backup. Valid values are 1, 2, and 3. Default is None, in wich case a best-fit is chosen automatically. Strategy 1 creates a single TAR from all the files and folders listed as source. Strategy 2 will use rsync to perform the backup copy. Strategy 3 uses rsync as well, but needs the destination to be a BTRFS file system to make snapshots of former backups, which will create a time-line of backups.

`--days-off NUM`: sets the number of days the retention plan is offset to the current date. I.e. if days-off is set to 3, the last three days will not be touched by the retention strategy, hence will not be touched. The default of this value is 2.

`--stay-on-fs`: If set, only those files from a source path which reside on the same file system will be added to the backup.

`--preserve-path`: If set, the path as stated in the source-dir arguments will be preserved.

`--ignore-errors`: Ignores rsync errors and keeps on working on a backup until finished with the sequence of its backup instructions. If errors occur during backup, chances are that the resulting backup is incomplete.

`--log-file FILENAME`: Sets the log file name. With this option, output will be written to the log file instead of std-out.

`--quiet`: No messages are written neither to std-out nor to a log-file.

`--dry-run`: Performs a trial run, which causes no changes.

`--version`: Prints the version of this script to std-out.
