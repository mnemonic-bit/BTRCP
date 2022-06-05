#!/usr/bin/python3



import argparse
import datetime
from datetime import timedelta
from enum import Enum
import getpass
import glob
import itertools
import os
import plumbum as pb
from prelude import identity, fst, snd, concat
import runcmdutils
from runcmdutils import Path, write_log, LogLevel, run_cmd, mk_cmd
import signal
import sys
import subprocess
from urllib.parse import urlparse




# This is the version of the script.
script_version='1.0.0'



class Environment:
    # This is the timestamp format string used by all strategies to create
    # a name that is unique and represents the moment in time that the backup
    # has been created.
    timestampFormatString = '%Y-%m-%d-%H-%M'
    # The glob-pattern matches the timestampFormatString for globbing through
    # a directory.
    timestampGlobPattern = '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]'

    # The number of days the retention strategy is offset. During this days
    # all backups that were made are kept, until they get older than 'days_off' days.
    days_off = 1

    # The name of the log-file.
    log_file_name = None

    # This is the backup strategy that will be used by this script
    # to do its job. By default we use a basic rsync-strategy
    backup_strategy = 2

    # Instructs the backup algorithm to stay on the file system if
    # this field is set True. By default btrcp does not honour
    # file system boundaries.
    stay_on_file_system = False

    # Tells rsync to ignore read-errors
    ignore_errors = False

    host_name = None
    source_dirs = []
    excluded_dirs = []
    dest_dir = '.'



# This is the script environment that holds all major settings and
# variables.
env = Environment



# Defines deltas which are translated into timedeltas and format strings
# to format the file's date.
class Deltas(Enum):
    Hour = 0    # strftime ('%H')
    Day = 1     # strftime ('%d')
    Week = 2    # strftime ('%W')
    Month = 3   # strftime ('%m')
    Year = 4    # strftime ('%Y')

# For each delta we have a format string that can be used to uniquely
# identify a date with respect to the granularity of that delta.
_deltaFormatStrings = { Deltas.Hour : '%Y-%m-%d-%H', Deltas.Day : '%Y-%m-%d', Deltas.Week : '%Y-%W', Deltas.Month : '%Y-%m', Deltas.Year : '%Y', None : '%Y-%m-%d-%H-%S' }


# Lists the time-spans and the number of times that timespan is to
# be used for retaining backups. This list will be sorted before
# it is used, but keeping it sorted in the first palce would'nt do
# much harm either.
retentionIntervals = [(Deltas.Day, 14), (Deltas.Week, 6), (Deltas.Month, 10), (Deltas.Year, 10)]



def init_arg_parser():
    parser = argparse.ArgumentParser(prog='btrcp', description='Backup utility for BTRFS.')
    parser.add_argument ('--source-dir', '-s', dest = 'source_dirs', required = True, action = 'append', default = [], metavar='PATH', help='Specifies a source directories to backup. This option can be used multiple times in one command.')
    parser.add_argument ('--exclude-dir', '-e', dest = 'excluded_dirs', required = False, action = 'append', default = [], metavar='PATH', help='Specifies a source directories to backup. This option can be used multiple times in one command.')
    parser.add_argument ('--dest-dir', '-d', dest = 'dest_dir', required = False, default='.', metavar='PATH', help='Specifies the destination directory where the backups will be written to.')
    parser.add_argument ('--hostname', dest = 'host_name', required = False, metavar = 'NAME', default = None, help = 'sets the alternate hostname to be used instead of the local machines own hostname.')
    parser.add_argument ('--strategy', dest = 'backup_strategy', required = False, metavar = 'NUM', default = 2, help = 'sets the backup strategy to use. Supported values are 1, 2, 3, 4.')
    parser.add_argument ('--days-off', dest = 'days_off_str', required = False, metavar = 'NUM', default = '1', help = 'set the number of days to offset the retention strategy, i.e. deletion of backups will only start after NUM days.')
    #parser.add_argument ('--exclude', '-e', dest = 'excludes', required = False, action = 'append', default = [], metavar = 'FILE', help = 'gives of files or directories to exclude from the backup.')
    parser.add_argument ('--stay-on-fs', dest = 'stay_on_file_system', required = False, action = 'store_const', const = True, help = 'recursion through sub-folders does not leave the bounds of a file-system.')
    parser.set_defaults (stay_on_file_system = False)
    parser.add_argument ('--ignore-errors', dest = 'ignore_errors', required = False, action = 'store_const', const = True, help = 'tells rsync (if used for the backup) to ignore read-errors.')
    parser.set_defaults (ignore_errors = False)
    parser.add_argument ('--log-file', '-l', dest = 'log_file_name', required = False, metavar = 'FILENAME', help = 'Specifies the name of a log file.')
    parser.add_argument ('--quiet', dest = 'silent_mode', required = False, action = 'store_const', const = True, help = 'Suppresses all console output of this script.')
    parser.set_defaults (silent_mode = False)
    parser.add_argument ('--dry-run', dest = 'dry_run', required = False, action = 'store_const', const = True, help = 'Make this a dry-run, actions are only logged.')
    parser.set_defaults (dry_run=False)
    parser.add_argument ('--version', action = 'version', version = '%(prog)s {0}'.format (script_version))
    return parser



def parse_args(*args):
    parser = init_arg_parser()
    return parser.parse_args(*args)



def get_user_info():
    user_id = os.getuid()
    user_name = getpass.getuser()
    return '{0} ({1})'.format (user_name, user_id)



def init_env (args):
    global env
    #env = args

    # At the moment we only support one backup strategy.
    #env.backup_strategy = 1
    # All excludes must be transformed if they contain wildcard characters.
    #env.excludes = ['^{0}$'.format (e.replace ('*', '.*')) for e in env.excludes]
    if (hasattr (env, 'excludes')):
        env.excludes = [Path (p) for p in env.excludes]
    # If '--silent' is set as a script parameter, we remove the stream-handler
    # from the logger.
    if (args.silent_mode):
        runcmdutils.remove_console_log_handler()
    # If there is a log-file name given in the list of options, we add a log
    # file handler for this.
    if (args.log_file_name):
        env.log_file_name = args.log_file_name
        runcmdutils.add_log_file_handler (env.log_file_name)
    # Converts the string of --days-off to an integer
    env.days_off = int (args.days_off_str)
    env.backup_strategy = int (args.backup_strategy)
    env.host_name = args.host_name
    env.source_dirs = args.source_dirs
    env.excluded_dirs = args.excluded_dirs
    env.dest_dir = args.dest_dir
    env.stay_on_file_system = args.stay_on_file_system
    env.ignore_errors = args.ignore_errors



# This map is used when the time-diff instance is created from a Delta
# instance.
_deltaMap = { Deltas.Hour : ('hours', 1), Deltas.Day : ('days', 1), Deltas.Week : ('days', 7), Deltas.Month : ('days', 30), Deltas.Year : ('days', 365) }

# Creates a time-diff instance from the Delta and the number of
# times that delta should be applied.
def _mk_timediff (delta, factor):
    p = _deltaMap[delta]
    return timedelta (**{ fst (p) : snd (p) * factor })



# Converts the definition of retention intervals with their counts
# into a list of absolute time bounds whose reference time is the
# current system time.
def _mk_datetime_boundaries():
    res = []
    now = datetime.datetime.now()
    base = now - _mk_timediff (Deltas.Day, env.days_off)
    for delta, factor in retentionIntervals:
        base -= _mk_timediff (delta, factor)
        res.append ((delta, base))
    return res



# Parses the file name and returns a datetime instance which
# represents the time equal to the name of the file.
def _mk_datetime_from_file_name (fileName):
    name = os.path.basename (fileName.rstrip (os.sep))
    return datetime.datetime.strptime (name, env.timestampFormatString)



# Groups the list of files according to the retention intervals that
# are defined globally. This function returns a list of tuples whose
# first element is the Deltas-instance and the second element is the
# list of files that belong to that Deltas-interval.
def _mk_delta_groups (files):
    bounds = _mk_datetime_boundaries()
    files.sort (reverse = True, key = snd)
    # filter those files that are younger than 'days_off'
    timeThreshold = datetime.datetime.now() - _mk_timediff (Deltas.Day, env.days_off)
    files = [f for f in files if snd (f) < timeThreshold]

    write_log ('Bounds based on the retention intervals: {0}'.format (bounds))

    # This variable stores the groups we build.
    grps = []
    grp = []

    idx = 0
    delta, lowerBound = bounds[idx]
    idx += 1
    for f in files:
        #write_log ('delta={0}, lowerBound={1}, file-date=\'{2}\''.format (delta, lowerBound, snd (f)))
        if (snd (f) > lowerBound):
            grp.append (f)
        else:
            if (idx < len (bounds)):
                grps.append ((delta, grp))
                grp = []
                grp.append (f)
                idx += 1
                delta, lowerBound = bounds[idx]
            else:
                delta = None
                grp.append (f)

    grps.append ((delta, grp))

    return grps



# Returns an appropriate format string to use in strftime for grouping
# dates accornding to the delta used.
def _delta_to_format_string (delta):
    return _deltaFormatStrings[delta]



# Receives a float as it is returned from a function call like
# os.path.getctime (fileName), and returns a string represenation
# suitable for grouping a list of floats with respect to a given
# time interval.
def _ctime_to_delta_string (tstmp, delta):
    return tstmp.strftime (_delta_to_format_string (delta))



# Groups the elements of a list, The grouping is based
# on equality of whatever the group-function returns. This function
# packs the grouped results into a list of tuples where the first
# element is the criteria that is shared by that group, and a list
# of elements belonging to that group. The list of elements per group
# has the same structure the input list had.
def _groupby (lst, group_fn):
    return [(k, [g for g in grp]) for k, grp in itertools.groupby (lst, group_fn)]



def _filter_all_but_max (grps, fn):
    res = []
    for grp in grps:
        mx = min (snd (grp), key = fn)
        res.append ((fst (grp), [e for e in snd (grp) if e != mx]))
    return res



# Takes a list of tuples of file names and their mtimes, and a time Delta
# this group lies in, and returns a new list which only contains those
# file names that can be removed.
def _find_unretained_files (files, delta):
    # Make a list of all file names that consists of tuples with their
    # first element being the group-by string based on the ctime of the
    # file, and the second element of the tuple bing the file name itself.
    #tpls = [(_ctime_to_delta_string (ctime, delta), (ctime, f)) for f, ctime in files]
    # Group this items according to the given delta.
    grps = _groupby (files, lambda x: _ctime_to_delta_string (snd (x), delta))
    # Remove all files that we want to keep from the list
    return _filter_all_but_max (grps, snd)



# Removes all files that are listed in the parameter.
def _remove_files (files):
    for file in files:
        _rm (file, is_folder = True if file.is_dir() else False)



# Removes old and no longer useful backup. The plan about how long
# backups are kept is stored in the global variable retentionIntervals.
# This is how the plan is implemented:
# 1) Cluster the files that match our backup-file pattern in the path
#    into groups; each group will contain only backup files that belong
#    to a single delta-period, e.g. one group may contain all backups 
#    that are in the 14 days period where we want to keep one backup
#    per day.
# 2) Find redundant backups in the list of each group.
# 3) Remove redundant backups from the file system. This step uses the
#    list we have obtained in step (2) and performs a delete-operation
#    on the file system to remove each backup which is listed in our
#    list.
def _execute_retention_plan (path, *, pattern = None):
    # Creates a list of files that lie in the given path and adds the
    # ctime of each file to each tuple of the list.
    if (not pattern):
        pattern = '*'
    #fileNames = [(f, datetime.datetime.fromtimestamp (os.path.getmtime (f.path))) for f in path.glob (pattern)]
    fileNames = [(f, _mk_datetime_from_file_name (f.path)) for f in path.glob (pattern)]

    # TODO: group the file names according to the retention intervals
    # which are globally defined.
    deltaGroups = _mk_delta_groups (fileNames)

    # For each interval defined in our list of retention-intervals we
    # go and remove the files that are not ment to be retained.
    for delta, grp in deltaGroups:
        fltrd = _find_unretained_files (grp, delta)
        write_log ('Old backups that are removal-candidates for delta {0}: {1}'.format (delta, fltrd))
        removeList = [fst (p) for p in concat ([snd (f) for f in fltrd])]
        write_log ('Old backups that are being removed for delta {0}: {1}'.format (delta, [p.path for p in removeList]))
        _remove_files (removeList)



# Creates a directory at the given location
def _mkdir (path):
    res = run_cmd (['mkdir', '-p', str(path)], machine = path.get_context())
    return res.returncode



# Moves a file from an old location/file-name to a new one.
def _mv (old, new):
    res = run_cmd (['mv', str(old), str(new)], machine = old.get_context())
    return res.returncode



# Removes the file given as path parameter.
def _rm (path, *, is_folder = False):
    cmd_args = ['rm', str (path)]
    if (is_folder):
        cmd_args = ['rm', '-r', str (path)]
    #cmd_args.extend (str (path))
    res = run_cmd (cmd_args, machine = path.get_context())
    return res.returncode



# Returns the hostname of the current machine.
def _hostname():
    res = run_cmd (['hostname'])
    return res.stdout.strip()



# Measures the size of the path.
def _du (path):
    cmd_args = ['du', '-shx', str (path)]
    res = run_cmd (cmd_args, machine = path.get_context())
    if (res.returncode == 0):
        return fst (res.stdout.rstrip().split())
    return None



# Creates a g-zipped tar file from the current work directory and writes
# the archive to the file given by the parameter backupFileName.
def _create_tar_of_directory (backupFileName, files, *, excludes = []):
    if (backupFileName.get_context() != pb.local):
        args = ['tar', '--numeric-owner', '-czf', '-']
        for ex in excludes:
            args.extend (['--exclude', str(ex)])
        args.extend ([str(f) for f in files])
        tar_cmd = mk_cmd (args)
        tee_cmd = mk_cmd (['tee', str(backupFileName)], machine = backupFileName.get_context())
        cmd = tar_cmd | tee_cmd
    else:
        args = ['tar', '--numeric-owner', '-czf', str(backupFileName)]
        for ex in excludes:
            args.extend (['--exclude', str(ex)])
        args.extend ([str(f) for f in files])
        tar_cmd = mk_cmd (args)
        cmd = tar_cmd
    res = cmd.run()
    # The return-code is stored in the first element of the result-triple
    # that is returned by the call to run().
    return fst (res)



# Calls 'rsync' in archive-mode. Please note that the source path must end
# with a separator character ('/') if it designates a directory. Conversely
# the source path must not end with a slash if it references a file instead
# of a folder.
def _rsync (source, dest, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    #src = source.join ('')
    dst = str (dest)
    if (dest.is_remote_path()):
        dst = dest.full_path()
    args = ['rsync', '-a', '-A', '--delete']
    if (stayOnFS):
        args.append ('-x')
    if (ignoreErrors):
        args.append ('--ignore-errors')
    for ex in excludes:
        args.extend (['--exclude', str(ex)])
    # If we sync a single file, we must not append a slash to the
    # path, otherwise rsync will run into an error.
    if (source.is_file()):
        _source = str (source)
    else:
        _source = str (source.join (''))
    # Extend the arguments of rsync with the source and destination.
    args.extend ([_source, dst])
    # TODO: add the option '-X' to that call after figuring out why
    # not all rsync calls succeed.
    res = run_cmd (args)
    return res.returncode



# Returns the path to the btrfs command binaries. This is needed to make sure
# that the PATH environment of the Python script includes it.
def _find_btrfs_cmd_path():
    res = run_cmd (['which', 'btrfs'])
    # If the result starts with a path-separator we suppose that its an actual
    # path as a result returned from the command 'which'. Otherwise it is an
    # error message.
    if (res.stdout.startswith (os.path.sep)):
        return os.path.dirname (res.stdout)
    return None



# Checks if the given path is a root node to a BTRFS subvolume and returns True
# if that is the case, or False otherwise.
# Note that this function returns False if the path reaches deeper beyond the
# root of the subvolume.
def _path_is_btrfs_subvolume (path):
    #> stat -f --format="%T" "$dir")" == "btrfs" => return 1
    #> stat --format="%i" "$dir" => 2 | 256 => return 0, otherwise return 1
    res = run_cmd (['stat', '-f', '--format=%T', str(path)], machine = path.get_context())
    out = res.stdout.strip()
    if (out != 'btrfs'):
        return False
    res = run_cmd (['stat', '--format=%i', str(path)], machine = path.get_context())
    out = int(res.stdout.strip())
    if (out in [2, 256]):
        return True
    return False



# Creates a BTRFS shanpshot for a given subvolume at the requested locatoin.
def _create_btrfs_subvolume (subvolPath):
    res = run_cmd (['btrfs', 'subvolume', 'create', str(subvolPath)], machine = subvolPath.get_context())
    return res.returncode



# Creates a BTRFS shanpshot for a given subvolume at the requested locatoin.
def _create_btrfs_snapshot (subvolPath, snapshotPath, *, readOnly = False):
    if (readOnly):
        res = run_cmd (['btrfs', 'subvolume', 'snapshot', '-r', str(subvolPath), str(snapshotPath)], machine = subvolPath.get_context())
    else:
        res = run_cmd (['btrfs', 'subvolume', 'snapshot', str(subvolPath), str(snapshotPath)], machine = subvolPath.get_context())
    return res.returncode



# returns the mount point from where the path actually starts in the current
# file system hirarchy.
def _get_mount_point (path):
    res = run_cmd (['stat', '-c', '%m', str(path)], machine = path.get_context())
    if (res.returncode == 0):
        return res.stdout.rstrip()
    return None



def _get_possible_mount_point (path):
    mountPoint = None
    p = path.path
    while (p != os.sep):
        mountPoint = _get_mount_point (path._copy (p))
        if (mountPoint):
            break
        p = os.path.dirname (p)
    return path._copy (mountPoint)



def _get_most_recent_backup_dir (hostName, destinationDir):
    destBaseDir = destinationDir.join (hostName)
    mostRecentBackupDir = max (destBaseDir.glob ('{0}/'.format (env.timestampGlobPattern)), key = lambda p: p.get_last_part(), default = None)
    return mostRecentBackupDir



# Implements the second backup strategy:
# Uses tar to zip up all source directories and write them as a single
# file to the destination directory.
def backup_strategy_1 (hostName, sourceDirs, destinationDir, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    tarBaseDir = destinationDir.join (hostName)
    _mkdir (tarBaseDir)

    tarFileName = datetime.datetime.now().strftime ('{0}.tar.gz'.format (env.timestampFormatString))
    tarBackupFile = tarBaseDir.join (tarFileName)

    backedUpFiles = []
    for dir in sourceDirs:
        backedUpFiles.extend (dir.glob ('*'))

    exitCode = _create_tar_of_directory (tarBackupFile, backedUpFiles)
    if (exitCode != 0):
        write_log ('Creating a tar-archive failed for host \'{0}\' with exit code \'{1}\''.format (hostName, exitCode))
        if (not _mv (tarBackupFile, tarBackupFile + '.err')):
            write_log ('Moving tar-archive during error handling failed for host \'{0}\'.'.format (hostName))
        return False

    write_log ('Backup file successfully created for host \'{0}\''.format (hostName))

    # At the end we remove old backups that are no longer needed.
    _execute_retention_plan (tarBaseDir, pattern = '*.tar.gz')

    return True



def backup_rsync_single_dir (sourceDir, destinationDir, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    # Measure the size of the backup
    write_log ('The size of the source {0} is: {1}.'.format (sourceDir.path, _du (sourceDir)))

    # If the source folder is part of the list of excluded directories,
    # then we stop here
    

    # We intend to write the sync-result to a destination folder
    # that identifies the host from which the data comes from, and
    # we also want to keep the folder structure as it was found on
    # the host system.
    destSourceDirExtension = str(sourceDir).strip (os.path.sep)
    dotSlashString = '.{0}'.format (os.path.sep)
    if (destSourceDirExtension.startswith (dotSlashString)):
        destSourceDirExtension = destSourceDirExtension.lstrip (dotSlashString)
    syncDestDir = destinationDir.join (destSourceDirExtension)

    # check if this is not a directory we have to sync a single
    # file instead. If its a file, we do not create a directory in the
    # destination location.
    if (sourceDir.is_file() != True):
        _mkdir (syncDestDir)
        sourceDir = sourceDir.join ('')

    exitCode = _rsync (sourceDir, syncDestDir, excludes = excludes, stayOnFS = stayOnFS, ignoreErrors = ignoreErrors)
    if (exitCode != 0):
        write_log ('Copying directory \'{0}\' with rsync failed with exit code \'{1}\''.format (sourceDir, exitCode))
        return False

    return True



def dir_is_excluded (sourceDir, excludedDirs):
    for excludedDir in excludedDirs:
        if sourceDir.path.startswith(excludedDir.path):
            return True
    return False



# Backs up multiple source directories using rsync.
def backup_rsync_source_dirs (sourceDirs, destinationDir, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    res = True
    for sourceDir in sourceDirs:
        for singleDir in sourceDir.glob():
            if not dir_is_excluded(singleDir, excludes):
                res &= backup_rsync_single_dir (singleDir, destinationDir, excludes = excludes, stayOnFS = stayOnFS, ignoreErrors = ignoreErrors)
    return res



# Implements the first backup strategy:
# Use plain file system folders and just copy the contents of the container
# main folder including its configuration file to the backup location. This
# method uses rsync to move all files between locatoins.
# This strategy does not execute any retention plan because it overwrites
# older backups in place.
def backup_strategy_2 (hostName, sourceDirs, destinationDir, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    rsyncDestDir = destinationDir.join (hostName)
    return  backup_rsync_source_dirs (sourceDirs, rsyncDestDir, excludes = excludes, stayOnFS = stayOnFS, ignoreErrors = ignoreErrors)



# The third strategy uses rsync to write the contents of the container base-
# directory to the backup destination. It also adds a layer of btrfs-subvolumes
# in the destination location to better track the backup process over time.
# This assumes that the backup destination has already set up a btrfs subvolume
# to snapshot. If the destination folder is not 
def backup_strategy_3 (hostName, sourceDirs, destinationDir, *, excludes = [], stayOnFS = True, ignoreErrors = False):
    destBaseDir = destinationDir.join (hostName)
    destDirName = datetime.datetime.now().strftime (env.timestampFormatString)
    destBtrfsDir = destBaseDir.join (destDirName)

    # Find the mount point of the destination directory and check
    # if it is a BTRFS subvolume, otherweise this strategy will not
    # work properly.
    mountPoint = _get_possible_mount_point (destBaseDir)
    if (not _path_is_btrfs_subvolume (mountPoint)):
        write_log ('The given destination directory is not a BTRFS subvolume and cannot be used as a destination for the choosen backup strategy 3 of host \'{0}\'.'.format (hostName))
        return False

    # Ensure that the destination base path exists and is a folder indeed.
    if (not destBaseDir.is_dir()):
        if (destBaseDir.exists()):
            write_log ('The destination director \'{0}\' already exists as a file. ({1})'.format (destBaseDir, hostName))
            return False
        _mkdir (destBaseDir)

    # Also ensure that the destination directory for the backup does not exist,
    # which we take as a sign that we would be overwriting someone else's data.
    if (destBtrfsDir.is_dir()):
        write_log ('The backup destination directory \'{0}\' already exists. ({1})'.format (destBtrfsDir, hostName))
        return False
    if (destBtrfsDir.exists()):
        write_log ('The backup destination directory \'{0}\' already exists as a file. ({1})'.format (destBtrfsDir, hostName))
        return False
        
    # Get the most recent backup:
    # This command lists all directories whose names match our date-pattern
    # we use when we create backup directories.
    mostRecentBackupDir = _get_most_recent_backup_dir (hostName, destinationDir)
    write_log ('The most recent backup of host \'{0}\' is \'{1}\''.format (hostName, mostRecentBackupDir))
    
    # if there is no backup to build on, we have to create a new subvolume
    if (mostRecentBackupDir == None or not _path_is_btrfs_subvolume (mostRecentBackupDir)):
        exitCode = _create_btrfs_subvolume (destBtrfsDir)
        if (exitCode != 0):
            write_log ('Creating a BTRFS subvolume failed with exit code {0}.'.format (exitCode))
            return False
    else:
        # Create a snapshot from the latest backup which we will use to rsync
        # our current contents to.
        exitCode = _create_btrfs_snapshot (mostRecentBackupDir, destBtrfsDir)
        if (exitCode != 0):
            write_log ('Creating BTRFS snapshot failed with exit code {0}.'.format (exitCode))
            return False

    # From here it really is the same as in strategy 2:
    # we just rsync everything to its destination directory, while
    # the destination is located inside a BTRFS volume or snapshot.
    backup_rsync_source_dirs (sourceDirs, destBtrfsDir, excludes = excludes, stayOnFS = stayOnFS, ignoreErrors = ignoreErrors)

    # At the end we remove old backups that are no longer needed.
    #_execute_retention_plan (destBaseDir, pattern = '{0}/'.format (env.timestampGlobPattern))

    return True



# Implements the 4th backup strategy:
# If the root filesystem of the container is a BTRFS subvolume, we can make
# use of this and create a snapshot, before sending the difference to the
# backup location itself.
def backup_strategy_4 (hostName, sourceDir, destinationDir, *, excludes = [], ignoreErrors = False):
    pass



# This is the main entry point for other scripts if this file is used as
# a module. The parameters passed to this method will come form the list
# of parameters if this file is started as a script.
def backup (hostName, sourceDirs, destinationDir, *, strategy = '2', excludes = [], days_off = 1, stayOnFS = True, ignoreErrors = False):
    # Defines for each backup strategy the function that implements it,
    # and a string pattern that can be used for globbing the destination
    # directory for backups.
    strategies = {1: backup_strategy_1, 2: backup_strategy_2, 3: backup_strategy_3, 4: backup_strategy_4}

    write_log ('Starting backup with strategy \'{0}\' for host \'{1}\''.format (strategy, hostName))
    # Turn all path-strings into Path-instances
    _src = [Path (p) for p in sourceDirs]
    _dst = Path (destinationDir)
    _excludes = [Path (p) for p in excludes]
    strategies[strategy](hostName, _src, _dst, excludes = _excludes, stayOnFS = stayOnFS, ignoreErrors = ignoreErrors)



def start_backup():
    # If no alternate hostname was passed as parameter to the script,
    # we query it from the system.
    if (env.host_name == None):
        env.host_name = _hostname()
    backup (env.host_name, env.source_dirs, env.dest_dir, strategy = env.backup_strategy, excludes = env.excluded_dirs, stayOnFS = env.stay_on_file_system, ignoreErrors = env.ignore_errors)



def inner_main(*args):
    args = parse_args (*args)
    init_env (args)
    start_backup()
    return 0



def signal_handler(sig, frame):
    print('Backup aborted.')
    sys.exit(0)



def main(*args):
    write_log ('Current user of the script is: \'{0}\''.format (get_user_info()), level=LogLevel.DEBUG)
    signal.signal(signal.SIGINT, signal_handler)
    return inner_main(*args)



def init_module():
    # Add the path to the btrfs command
    #btrfsCmdPath = _find_btrfs_cmd_path()
    #if (btrfsCmdPath):
    #    runcmdutils.add_env_path (btrfsCmdPath)
    pass



# Used as module or as script, it has to be initialized either way.
init_module()



# Start the main method if we were called as a script.
if __name__ == '__main__':
    sys.exit(main())


