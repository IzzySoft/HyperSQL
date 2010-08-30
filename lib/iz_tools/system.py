#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id$
"""
Some useful system functions which mostly mimic PHP (or Shell) equivalents
"""

#====================================================[ Imports and Presets ]===
import os       # for which() and getCallingModule()
import sys      # for which()
from subprocess import Popen,PIPE   # for popen()
from typecheck import *             # for file_put_contents (local module typecheck)
from traceback import extract_stack # for getCaller()

# prepare for fopen (encoding fallback)
from locale import getdefaultlocale
lc, encoding = getdefaultlocale()
encoding = encoding or 'UTF-8'
try:
    import codecs
except:
    codecs = None

#==============================================================[ Functions ]===
#------------------------------------------------------------------[ which ]---
def which(executable, path=None):
    """
    Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']). Mimics the shell command "which".
    Returns the complete filename or None if not found
    Original Source: http://snippets.dzone.com/posts/show/6313
    @param string executable to look for
    @param optional string path to look in
    @return string path/to/executable or None
    """
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    extlist = ['']
    if os.name == 'os2':
        (base, ext) = os.path.splitext(executable)
        # executable files on OS/2 can have an arbitrary extension, but
        # .exe is automatically appended if no dot is present in the name
        if not ext:
            executable = executable + ".exe"
    elif sys.platform == 'win32':
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in pathext:
            extlist = pathext
    for ext in extlist:
        execname = executable + ext
        if os.path.isfile(execname):
            return execname
        else:
            for p in paths:
                f = os.path.join(p, execname)
                if os.path.isfile(f):
                    return f
    else:
        return None

#------------------------------------------------------------------[ popen ]---
def popen(command):
    """
    Run a command and return its output as string. Mimics he PHP function
    "shell_exec" - with the difference of returning a touple, so stderr is
    also available to evaluation.
    Example call:  mylist, myerr = run('ls -l')
    @param string command
    @return string stdout, string stderr
    """
    p = Popen(command, shell=True,stdout=PIPE,stderr=PIPE)
    out = ''.join(p.stdout.readlines() )
    outerr = ''.join(p.stderr.readlines() )
    return out, outerr

#-------------------------------------------------------------[ shell_exec ]---
def shell_exec(command):
    """
    Run a command and return its output as string. Mimics he PHP function
    "shell_exec".
    Example call:  mylist = run('ls -l')
    @param string command
    @return string stdout
    """
    out, err = popen(command)
    return out

#------------------------------------------------------------------[ fopen ]---
def fopen(filename,mode,enc=None):
    """
    Wrapper to open a file either via codecs (if possible), or simply with open()
    (if codecs==None). If the third parameter is not set, it tries to read the
    global variable "encoding" instead. If that's not set either, fallback to
    open()
    This rawly mimics the PHP function fopen() up to the mandatory parameters,
    but differs with the optionals.
    @param string filename
    @param string mode
    @param optional string encoding
    @return filehandle
    """
    if enc is None:
        try:
            enc = encoding
        except:
            enc = None
    if codecs is None:
        enc = None
    if enc is None:
        return open(filename,mode)
    else:
        return codecs.open(filename,mode,enc)

#------------------------------------------------------[ file_get_contents ]---
def file_get_contents(filename,enc=None):
    """
    Get the content of the specified file and return it as string. Mimics the
    PHP function with the same name up to the mandatory parameter - but differs
    when it comes to the optionals.
    @param string filename name of the file to read
    @param optional string enc encoding of the file (defaults to system standard
           evaluated via locale settings)
    @return string text
    """
    infile = fopen(filename,'rb',enc)
    text = infile.read()
    infile.close()
    return text

#---------------------------------------------------------[ file_get_lines ]---
def file_get_lines(filename,enc=None):
    """
    Get the content of the specified file and return it as list. To be used
    like the PHP function file() - except for the optional parameter(s).
    @param string filename name of the file to read
    @param optional string enc encoding of the file (defaults to system standard
           evaluated via locale settings)
    @return list text
    """
    infile = fopen(filename,'rb',enc)
    list = infile.readlines()
    infile.close()
    return list

#------------------------------------------------------[ file_put_contents ]---
def file_put_contents(filename,content,enc=None,append=False):
    """
    Write the content to the specified file. To be used like the PHP function
    with the same name - except for the optional parameters.
    @param string filename name of the file to be written
    @param mixed content what should be written to the file. This can be either
           a string or a list
    @param optional string enc encoding of the file (defaults to system standard
           evaluated via locale settings)
    @param optional boolean append whether content shall be appended if the file
           already exists. By default, an existing file will be simply replaced.
    """
    if is_string(content): pass
    elif is_list(content): content = '\n'.join(content)
    else:
        raise TypeError, 'Second argument to file_put_contents must be either str or list, %s given' % is_what(content)
    if append: mode = 'ab'
    else: mode = 'wb'
    outfile = fopen(filename,mode)
    outfile.write(content)
    bytes = outfile.tell()
    outfile.close()
    return bytes

#--------------------------------------------------[ Caller identification ]---
def getCaller(level=3):
    """
    Find out who called the holding function
    @param optional integer level 1 = self, 2 = caller of GetCaller, 3 = who called 2, etc.
    @return tuple caller (filename, line number, function name, text)
    """
    stack = extract_stack()
    return stack[len(stack)-level]

def getCallingModule(level=4,basename=True):
    """
    Obtain the name of the calling module
    @param optional integer level 1 = self, 2 = caller of GetCaller, 3 = caller of getCallingModule, 4 = who called 3 (default), etc.
    @param optional boolean basename whether to cut-off the path (default: True)
    @return string name of the module (i.e. filename w/o ext)
    """
    return os.path.splitext(os.path.basename(getCaller(level)[0]))[0]
