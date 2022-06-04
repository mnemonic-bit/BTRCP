#!/usr/bin/python3



import argparse
import btrcp
import configparser
import datetime
from datetime import timedelta
from enum import Enum
import functools
import getpass
import glob
import os
import re
import runcmdutils
from runcmdutils import write_log, LogLevel, run_cmd
import shutil
import sys
import subprocess
import traceback



# This is the version of the script.
script_version='1.0.0'



# This is the script environment that holds all major settings and
# variables.
env = {}


def init_arg_parser():
    parser = argparse.ArgumentParser(prog='backup-lxc-container', description='Backup or restore of LXC containers.')
    parser.add_argument ('--base-dir', '-b', dest = 'base_dir', required = True, default='.', metavar='PATH', help='Specifies the base directory of the LXC containers.')
    parser.add_argument ('--dest-dir', '-d', dest = 'dest_dir', required = False, default='.', metavar='PATH', help='Specifies the destination directory where the backups will be written to.')
    parser.add_argument ('--name', '-n', dest = 'container_name', required = False, default='', metavar='NAME', help='Specifies the name of the container to backup.')
    parser.add_argument ('--no-enforce-stop', '-s', dest = 'enforce_stop_container', required = False, action = 'store_const', const = False, help = 'backup all containers in the base directory. If a list of excludes is given, those will be omitted.')
    parser.set_defaults (enforce_stop_container = True)
    parser.add_argument ('--strategy', dest = 'backup_strategy', required = False, metavar = 'NUM', default = '1', help = 'sets the backup strategy to use. Supported values are 1, 2, 3, 4.')
    parser.add_argument ('--all-containers', dest = 'backup_all_containers', required = False, action = 'store_const', const = True, help = 'backup all containers in the base directory. If a list of excludes is given, those will be omitted.')
    parser.set_defaults (backup_all_containers = False)
    parser.add_argument ('--only-running-containers', dest = 'backup_only_running_containers', required = False, action = 'store_const', const = True, help = 'Backup all containers that are currently running.')
    parser.set_defaults (backup_only_running_containers = False)
    parser.add_argument ('--only-stopped-containers', dest = 'backup_stopped_containers', required = False, action = 'store_const', const = True, help = 'Backup all containers that are currently stopped.')
    parser.set_defaults (backup_stopped_containers = False)
    parser.add_argument ('--exclude', '-e', dest = 'excludes', required = False, action = 'append', default = [], metavar = 'CONTAINERNAME', help = 'list of containers to exclude from the backup.')
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
    env = args
    # At the moment we only support one backup strategy.
    #env.backup_strategy = 1
    # All excludes must be transformed if they contain wildcard characters.
    env.excludes = ['^{0}$'.format (e.replace ('*', '.*')) for e in env.excludes]
    # The flag backup_all_containers is true if it has been set directly,
    # or if one of the other two options --only-running-containers or 
    # --only-stopped-containers has been set.
    env.backup_all_containers = env.backup_all_containers or env.backup_stopped_containers or env.backup_only_running_containers
    # The options --only-running-containers and --only-stopped-containers
    # are in conflict with each other. We declare the latter option to have
    # precedence over the former one by overwriting its value if both options
    # are set at the same time.
    if (env.backup_only_running_containers and env.backup_stopped_containers):
        env.backup_only_running_containers = False
    # Because the option --only-stopped-containers has precedence over the
    # other options, we will remove --enforce-stop if it is set, since
    # this would create trouble in the function backup_lxc_container() if
    # both flags are True at the same time.
    if (env.backup_stopped_containers):
        env.enforce_stop_container = False
    # If '--silent' is set as a script parameter, we remove the stream-handler
    # from the logger.
    if (env.silent_mode):
        runcmdutils.remove_console_log_handler()
    # If there is a log-file name given in the list of options, we add a log
    # file handler for this.
    if (env.log_file_name != None):
        runcmdutils.add_log_file_handler (env.log_file_name)



# Checks if a container name has been excluded by the --exclude
# command line option of this script.
def container_is_excluded (containerName):
    # This is basically just the same as in Haskell
    # "foldr (&&) True $ map (\ex -> regex_match ex containerName) env.excludes"
    return functools.reduce (lambda a, b: a or b, [bool (re.search (ex, containerName)) for ex in env.excludes], False)



# Implements the second backup strategy:
# Uses tar to zip up the whole container including its configuration file and
# root file system and writes the results to a backup location.
def backup_lxc_strategy_1 (containerName):
    sourceDir = os.path.join (env.base_dir, containerName)
    return btrcp.backup (containerName, [sourceDir], env.dest_dir, strategy = 1)



# Implements the first backup strategy:
# Use plain file system folders and just copy the contents of the container
# main folder including its configuration file to the backup location. This
# method uses rsync to move all files between locatoins.
def backup_lxc_strategy_2 (containerName):
    sourceDir = os.path.join (env.base_dir, containerName)
    return btrcp.backup (containerName, [sourceDir], env.dest_dir, strategy = 2)



# The third strategy uses rsync to write the contents of the container base
# directory to the backup destination, but also adds a layer of btrfs-subvolumes
# in the destination locatoin to better track the backup process over time.
# This assumes that the backup destination has already set up a btrfs subvolume
# to snapshot. If the destination folder is not 
def backup_lxc_strategy_3 (containerName):
    sourceDir = os.path.join (env.base_dir, containerName)
    os.chdir (sourceDir)
    return btrcp.backup (containerName, ['*'], env.dest_dir, strategy = 3, excludes = env.excludes)



# Implements the 4th backup strategy:
# If the root filesystem of the container is a BTRFS subvolume, we can make
# use of this and create a snapshot, before sending the difference to the
# backup location itself.
def backup_lxc_strategy_4 (containerName):
    sourceDir = os.path.join (env.base_dir, containerName)
    return btrcp.backup (containerName, [sourceDir], env.dest_dir, strategy = '4')



def backup_stopped_lxc_container (containerName):
    strategies = {'1': backup_lxc_strategy_1, '2': backup_lxc_strategy_2, '3': backup_lxc_strategy_3, '4': backup_lxc_strategy_4}
    strategies[env.backup_strategy](containerName)



# Checks the state of an LXC container. The result will be
# one of the folloging values encoded as UTF-8.
#
# RUNNING: indicated that the container is running
# STOPPED: the container is not running
# ???    : [TODO find out what that third state is to document its value]
# UNKNOWN: this value will be set by the function if none of the expected
#          values was returned.
#
# Returns a string in UTF-8 encoding.
def get_lxc_container_state (containerName):
    #> lxc-info -n $CONTAINER_NAME -s -H
    res = run_cmd (['lxc-info', '-P', env.base_dir, '-s', '-H', '-n', containerName])
    out = res.stdout.rstrip()
    if (out not in ['RUNNING', 'STOPPED', '???']):
        write_log ('Unknown container state returned by system call: \'{0}\''.format (out))
        out = 'UNKNOWN'
    return out



def stop_lxc_container (containerName):
    #> lxc-stop --nokill -t 18000 -n $CONTAINER_NAME
    res = run_cmd (['lxc-stop', '--nokill', '-t', '18000', '-P', env.base_dir, '-n', containerName])
    return res.returncode



def start_lxc_container (containerName):
    #> lxc-start -n $CONTAINER_NAME
    res = run_cmd (['lxc-start', '-P', env.base_dir, '-n', containerName])
    return res.returncode



def backup_lxc_container (containerName):
    write_log ('Backing up LXC container \'{0}\''.format (containerName))
    
    write_log ('Checking if container \'{0}\' is excluded from backup.'.format (containerName))
    if (container_is_excluded (containerName)):
        write_log ('The container \'{0}\' is excluded from backup via the --exclude option.'.format (containerName))
        return False

    containerState = get_lxc_container_state (containerName)
    write_log ('The current state of the container \'{0}\' is \'{1}\''.format (containerName, containerState))

    backupOnlyRunningContainers = env.backup_only_running_containers
    if (backupOnlyRunningContainers and containerState != 'RUNNING'):
        write_log ('Only containers which are currently running will be backed up because the command line option --only-running-containers is set. Aborting backup for container \'{0}\''.format (containerName), LogLevel.ERROR)
        return False

    backupOnlyStoppedContainers = env.backup_stopped_containers
    if (backupOnlyStoppedContainers and containerState != 'STOPPED'):
        write_log ('Only containers which are currently stopped will be backed up because the command line option --only-stopped-containers is set. Aborting backup for container \'{0}\''.format (containerName), LogLevel.ERROR)
        return False

    enforceStopContainer = env.enforce_stop_container
    containerWasStoppedByScript = False
    
    # if the container is running, we try to shut it down.
    if (enforceStopContainer and containerState == 'RUNNING'):
        exitCode = stop_lxc_container (containerName)
        if (exitCode != 0):
            write_log ('Stopping container \'{0}\' failed with exit code \'{1}\''.format (containerName, exitCode), LogLevel.ERROR)
            return False
        containerWasStoppedByScript = True
    
    # Check the container's state once again to make sure that
    # we work with a container that is really in the state STOPPED
    containerState = get_lxc_container_state (containerName)
    if (enforceStopContainer and containerState != 'STOPPED'):
        write_log ('Container \'{0}\' is not in the correct state for a backup. The current state is \'{1}\''.format (containerName, containerState))
        return False
    
    # Now use the selected/appropriate backup strategy
    try:
        backup_stopped_lxc_container (containerName)
    except Exception as e:
        write_log ('Copying of container "{0}" threw an exception: {1}'.format (containerName, e), LogLevel.ERROR)
        write_log ('The traceback for this is {0}'.format (traceback.format_exc()), LogLevel.ERROR)

    # At the end, restart the container again, if it was stopped by this script
    if (containerWasStoppedByScript):
        exitCode = start_lxc_container (containerName)
        if (exitCode != 0):
            write_log ('Starting container \'{0}\' failed with exit code \'{1}\''.format (containerName, exitCode), LogLevel.ERROR)
            return False

    return True



def backup_all_lxc_containers():
    basePath = env.base_dir
    folders = glob.glob (os.path.join (basePath, '*/'))
    res = True
    for folderPath in folders:
        folderName = folderPath[len (basePath) : ].strip (os.sep)
        res &= backup_lxc_container (folderName)
    return res



def start_backup():
    write_log ('Excluding this containers from the backup: {0}'.format (env.excludes))
    write_log ('The PATH we are using for this script is: {0}'.format (os.environ['PATH']))
    if (env.container_name):
        res = backup_lxc_container (env.container_name)
    else:
        res = backup_all_lxc_containers()
    return res



def inner_main(*args):
    args = parse_args (*args)
    init_env (args)
    return start_backup()



def main(*args):
    write_log ('Current user of the script is: \'{0}\''.format (get_user_info()))
    return inner_main(*args)



if __name__ == '__main__':
    sys.exit(main())

