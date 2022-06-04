# This is a module which provides an easy way to the subprocess API
# It will be used as a standardized way to access shell commands.



from enum import Enum
import logging
import os
import glob
import plumbum as pb
import sys
import subprocess
from urllib.parse import urlparse




# This will be set to True as soon as the function init_log() is called.
# It will prevent initializeing the logger compoment more than once.
_logger_is_initialized = False

# This is the logger reference that we use throughout this script.
_log = logging.getLogger (__name__)
#log.setLevel (logging.DEBUG)

# The log-format to be used for all logging activities
_logFormat = '%(asctime)-15s  %(message)s'

# The log-formatter instance to be used for several logger streams
_logFormatter = logging.Formatter (_logFormat)

# The instance of the condole log-handler which is used to write
# all logging data to stdout and stderr.
_stdoutHandler = logging.StreamHandler (stream = sys.stdout)
_stderrHandler = logging.StreamHandler (stream = sys.stderr)

# Stores the environment uesd to execute all commands.
_env = None



# A class container for returning the results of shell-sub-process calls.
class ProcessResult:
    __slots__ = []



def init_logger():
    global _logger_is_initialized
    if (_logger_is_initialized == True):
        return
    _logger_is_initialized = True
    _stdoutHandler.setFormatter (_logFormatter)
    _stderrHandler.setFormatter (_logFormatter)
    _log.addHandler (_stdoutHandler)
    #log.addHandler (stderrHandler)
    _log.setLevel (logging.INFO)



# Adds a log-file handler to the logger instance we use in this script.
def add_log_file_handler (fileName):
    fileHandler = logging.FileHandler (fileName, mode = 'a', encoding = 'UTF-8')
    fileHandler.setFormatter (_logFormatter)
    _log.addHandler (fileHandler)



# Removes the handler for writing log messages to the console. This function
# is called when the option '--silent' has been given to this script.
def remove_console_log_handler():
    global _stdoutHandler, _stderrHandler
    if (_stdoutHandler != None):
        _log.removeHandler (_stdoutHandler)
        _stdoutHandler = None
    if (_stderrHandler != None):
        _log.removeHandler (_stderrHandler)
        _stderrHandler = None


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR



def write_log (msg, level = LogLevel.INFO):
    log_functions = {LogLevel.DEBUG: _log.debug, LogLevel.INFO: _log.info, LogLevel.WARNING: _log.warning, LogLevel.CRITICAL: _log.critical, LogLevel.ERROR: _log.error}
    log_functions[level](msg)



# Stores the references to the plumbum machine instances used in this script.
# NOTE: This variable should not be used anywhere except the function
# _select_machine_context(...).
_machines = {}



def _mk_ssh_opts (hostkey):
    ssh_opts = ()
    scp_opts = ()
    if (hostkey):
        ssh_opts = ('-o', 'UserKnownHostsFile={0}'.format (hostkey))
        scp_opts = ('-o', 'UserKnownHostsFile={0}'.format (hostkey))
    return (ssh_opts, scp_opts)



def _mk_maching_context (username, hostname, *, port = None, password = None, opts = None):
    if (opts == None):
        raise Exception ('The parameter \'opts\' cannot be None.')
    new_machine = None
    if (hostname):
        new_machine = pb.SshMachine (hostname, port = port, user = username, password = password, ssh_opts = opts[0], scp_opts = opts[1])
    else:
        new_machine = _get_local_machine_context()
    return new_machine



# Returns an appropriate (plumbum-) machine instance for the path.
# The path that is given as parameter for this function must be a
# ParseResult of a parseurl()-call.
def _select_machine_context (username, hostname, *, port = None, password = None, hostkey = None):
    global _machines
    key = '{0}@{1}:{2}'.format (username, '' if hostname == None else hostname, '' if port == None else str (port))
    ssh_opts = _mk_ssh_opts (hostkey)
    if (key not in _machines or key in _machines and not _machines[key][1] == ssh_opts[0]):
        new_machine = _mk_maching_context (username, hostname, port = port, password = password, opts = ssh_opts)
        _machines[key] = (new_machine, *ssh_opts)
    return _machines[key][0]



# Returns the local machine context
def _get_local_machine_context():
    return pb.local



# This path-class represents all we need to know about paths that are
# used in this module or script.
class Path(object):
    path = None
    _machinePath = None
    _machineContext = None
    _hostname = None
    _port = None
    _username = None

    def __init__ (self, path = None, * , machine = None):
        if (path is not None and not isinstance (path, str)):
            raise EnvironmentError()
        # For the copy constructor, just return
        if (not path):
            self.path = None
            self._machineContext = None
            self._hostname = None
            self._username = None
            return

        # Add a scheme, if no scheme was given, assumint that it is SSH
        if (':' in path):
            if ('://' not in path):
                path = 'ssh://' + path

        parsedUri = urlparse (path)
        self._hostname = parsedUri.hostname
        self._username = parsedUri.username
        self._port = parsedUri.port
        if (machine):
            self._machineContext = machine
        else:
            self._machineContext = _select_machine_context (parsedUri.username, parsedUri.hostname)
        #self.path = self._machineContext.env.expanduser (parsedUri.path)
        self.path = parsedUri.path
        self._machinePath = self._machineContext.path (parsedUri.path)

    # This is the copy-constructor.
    def _copy (self, path):
        if (not isinstance (path, str)):
            raise EnvironmentError()
        newPath = Path()
        newPath.path = path
        newPath._machinePath = self._machineContext.path (path)
        newPath._machineContext = self._machineContext
        newPath._hostname = self._hostname
        newPath._port = self._port
        newPath._username = self._username
        return newPath

    # Expands user-directories which in Linux this is represented by a tilde (~)
    # into an absolute path.
    def expanduser (self):
        expanded_path = self._machineContext.env.expanduser (self.path)
        return self._copy (expanded_path)

    # Returns True if the path points to a remote machine.
    def is_remote_path (self):
        return True if self._hostname else False

    # Returns True if the given path represents the root of the file system.
    def is_root (self):
        return self.path == os.path.sep

    # Returns true if the object this path represents exist.
    def exists (self):
        return self._machinePath.exists()

    # Returns true if the path represents a directory
    def is_dir (self):
        return self._machinePath.is_dir()

    # Returns True if the path represents a file.
    def is_file (self):
        return self._machinePath.is_file()

    # Returns the last part of this Path, which is either
    # the file name the path points to, or the folder name
    # if this path points to a directory. The returned part
    # is of type String.
    def get_last_part (self):
        return os.path.basename (os.path.normpath (self.path))

    # Strips the base folders of this path and returns a string
    # which consists of everyting that was added to this path
    # instance compared to the path which is given as parameter.
    # To make is more consistent with conventions about absolute
    # paths, the string returned will not start with a slash or
    # os-separator character.
    def strip_base (self, path):
        res = None
        if (not isinstance (path, Path)):
            raise EnvironmentError()
        p = path.path
        if (self.path.startswith (p)):
            res = self.path[len (p):]
            if (res.startswith (os.sep)):
                res = res[1:]
        return res

    # Joins multiple path fragments together to a single path.
    def join (self, *args):
        return self._copy (os.path.join (self.path, *args))

    # Enumerates all files and folders containes in the directory
    # this path represents.
    def glob (self, pattern = None):
        # We need os.path.join to join the path and the pattern,
        # because the plumbum-lib has a prolem with patterns that
        # end with a os.path.sep character.
        globPath = self.path
        if pattern is None:
            pattern = '*'

        self._machineContext.cwd.chdir(globPath)

        return [self._copy (g) for g in self._machineContext.cwd.glob(pattern)]

    # Changes the working directory to the path this instance represents.
    def change_work_dir (self):
        return self._machineContext.cwd(self._machinePath)

    # Returns the machine context this path is defined in.
    def get_context (self):
        return self._machineContext

    # Returns the full path representation as a string.
    def full_path (self):
        return '{0}@{1}:{2}'.format(self._username, self._hostname, self.path) if self.is_remote_path() else self.path

    def __str__ (self):
        # Returns the path description in full detail as a string.
        # If this is a remote path we add the username and hostname
        # to the path, otherwise the local part of the path is just
        # returned as a string.
        return self.path

    # Returns the plumbum-path instance this path-instance is wrapping.
    def pbPath(self):
        # Returns the Plumbum path representation of this Path instance
        return self._machinePath



# Returns a machine represenation for the remote host
def get_machine (username, hostname, *, port = None, password = None, hostkey = None):
    return _select_machine_context (username, hostname, port = port, password = password, hostkey = hostkey)



# Creates a command wrapper which contains the command name and its arguments.
# This wrapper can then be piped or directly executed by calling its run() method.
def mk_cmd (args, *, machine = None, stdin = None):
    write_log ('Building command \'{0}\''.format(' '.join ([a if isinstance (a, str) else str(a) for a in args])), level = LogLevel.DEBUG)

    # Figure out on which machine we will execute the command.
    # If no machine is given, then we will run the command on the 
    # local machine.
    if (machine == None):
        machine = pb.local

    cmd = machine[args[0]][args[1:]]
    if (stdin):
        cmd = cmd << stdin

    # Return a command wrapper that can be executed later or piped
    # together with other commands.
    return cmd


def exec_cmd (cmd):
    global _env

    write_log ('Executing command \'{0}\''. format(str(cmd)), level = LogLevel.INFO)

    res = cmd.run (retcode = None, env = _env)

    # Log the output
    stdout = res[1]
    if (stdout): write_log (stdout, level = LogLevel.INFO)
    stderr = res[2]
    if (stderr): write_log (stderr, level = LogLevel.ERROR)

    # Create a new instance to return the results of the subprocess call.
    procRes = ProcessResult
    procRes.returncode = res[0]
    procRes.stdout = stdout
    procRes.stderr = stderr

    # Return the result of the shell-command.
    return procRes



# Calls a shell command. If 'stdin' is given, it will be passed through
# the stdin-pipe of the shell to the command. If 'dryRun' is set to True
# the command is not executed, but instead an empty result with a return-code
# of 0 and empty stdout and stderr results is returned.
def run_cmd (args, *, machine = None, stdin = None):
    global _env

    cmd = mk_cmd (args, machine = machine, stdin = stdin)

    return exec_cmd (cmd)



# Copies via scp from src to dst.
# NOTE that both parameters must be instances of plumbum.Path
def scp (src, dst):
    if (not isinstance (src, Path) or not isinstance (dst, Path)):
        return None
    return pb.path.utils.copy (src.pbPath(), dst.pbPath())



# Sets the path of the environment to the value passed as parameter
def set_env_path (path):
    global _env
    _env['PATH'] = path



# Adds the path given as parameter to the current value of the path
# of the environment. Of elements of the path to add already exist
# in the environment they will not be added again.
def add_to_env_path (path):
    global _env
    currentPathElements = _env['PATH'].split(':')
    addPathElements = []
    for p in path.split(':'):
        if (not p in currentPathElements):
            addPathElements.append (p)
    newPath = ':'.join (addPathElements + currentPathElements)
    _env['PATH'] = newPath



# Initializes this module.
def init_module():
    init_logger()
    # Make a copy of the system environment to have one of our own.
    global _env
    _env = os.environ.copy()



#def __init__():
#    init_logger()

init_module()


