#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Some useful system functions
"""

#====================================================[ Imports and Presets ]===
import os       # for which()
import sys      # for which()
from subprocess import Popen,PIPE   # for popen()
from types import *  # for type checking

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
    """Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']).  Returns the complete filename or None if not
    found
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
    Run a command and return its output as string. Example call:
    mylist = run('ls -l')
    @param string command
    @return string stdout, string stderr
    """
    p = Popen(command, shell=True,stdout=PIPE,stderr=PIPE)
    out = ''.join(p.stdout.readlines() )
    outerr = ''.join(p.stderr.readlines() )
    return out, outerr

#------------------------------------------------------------------[ fopen ]---
def fopen(filename,mode,enc=None):
    """
    Wrapper to open a file either via codecs (if possible), or simply with open()
    (if codecs==None). If the third parameter is not set, it tries to read the
    global variable "encoding" instead. If that's not set either, fallback to
    open()
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

#----------------------------------------------------------[ Type checking ]---
"""
Type checking functions have been taken from:
http://code.activestate.com/recipes/305888-a-way-to-deal-with-checking-for-types/
"""
def check_type(obj,atts=[],callables=[]):
    """
    Helper for is_mapping(), is_list(), is_str() and is_file()
    @param object object to check
    @param optional list atts attributes the object must have (default: empty list)
    @param optional list callables callables the object must have (default: empty list)
    """
    got_atts=True
    for att in atts:
      if not hasattr(obj,att):
        got_atts=False;break
    got_callables=True
    for call in callables:
      if not hasattr(obj,call):
        got_callables=False;break
        the_attr=getattr(obj,call)
        if not callable(the_attr):
          got_callables=False;break
    if got_atts and got_callables: return -1
    return 0

def is_iter(obj):
    """
    Check whether the object is iterable
    @param object object to check
    @return int 1 if True, 0 if False, -1 if iterable but neither list, tuple, dict or file
    """
    if isinstance(obj,ListType): return 1
    if isinstance(obj,TupleType): return 1
    if isinstance(obj,DictType): return 1
    if isinstance(obj,FileType): return 1
    if hasattr(obj,'__iter__') : return -1
    return 0

def is_gen(obj):
    """
    Is the object a generator?
    @param object object to check
    @return int 1 if True, 0 if False
    """
    if isinstance(obj,GeneratorType): return 1
    return 0

def is_seq(obj):
    """
    Is the object a sequence?
    @param object object to check
    @return int 1 if True, 0 if False, -1 if obj[0:0] works but it's neither list nor tuple (but e.g. str)
    """
    if isinstance(obj,ListType): return 1
    if isinstance(obj,TupleType): return 1
    if is_iter(obj):
      try: 
         obj[0:0]
         return -1
      except TypeError:
         pass
    return 0  
   
def is_mapping(obj):
    """
    Is the object a mapping type (e.g. dictionary)?
    @param object object to check
    @return int 1 if True, 0 if False, -1 if it's not a dict but has callables
    """
    if isinstance(obj,DictType): return 1
    if is_iter(obj):
      return check_type(obj,callables=['iteritems','has_key'])
    return 0

def is_dict(obj):
    """
    Is it a dictionary?
    @param object object to check
    @return int 1 if True, 0 if False, -1 if it's not a dict but has callables
    """
    return is_mapping(obj)

def is_list(obj):
    """
    Is the object a list?
    @param object object to check
    @return int 1 if True, 0 if False, -1 if it's not a list, but has callables append, extend, and pop
    """
    if isinstance(obj,ListType): return 1
    if is_seq(obj):
      if check_type(obj,callables=['append','extend','pop']): return -1
    return 0

def is_str(obj):
    """
    Is the object a string?
    @param object object to check
    @return int 1 if True, 0 if False, -1 not str but has callables index, count, and replace
    """
    if isinstance(obj, basestring): return 1
    if is_iter(obj):
      if check_type(obj,callables=['index','count','replace']): return -1
    return 0

def is_string(obj):
    """ alias for is_str """
    return is_str(obj)

def is_int(obj):
    """
    Is it an integer?
    """
    if isinstance(var, int) : return 1
    return 0

def is_numeric(var):
    """
    Is it a number - i.e. an integer or float?
    """
    try:
        float(var)
        return 1
    except ValueError:
        pass
    return 0

def is_file(obj):
    """
    Is the object a file?
    @param object object to check
    @return int 1 if True, 0 if False, -1 if it's not FileType but has callables read and close
    """
    if isinstance(obj,FileType): return 1
    if check_type(obj,callables=['read','close']): return -1
    return 0

def is_what(obj):
    """
    Get the type of the passed object
    @param object object to check
    @return mixed string category (if we have a direct match) or list of 0/1 [iter,gen,seq,list,str,dict,file]
    """
    try:
        if obj.__class__.__name__: return obj.__class__.__name__
    except:
        return [ str(i) for i in (is_iter(obj),is_gen(obj),is_seq(obj),is_list(obj),is_str(obj),is_mapping(obj),is_file(obj))]

