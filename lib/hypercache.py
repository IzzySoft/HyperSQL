"""
$Id$
HyperSQL simple Cache
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

import os
from dircache import listdir
import cPickle
from systools import fopen

class cache(object):
    """ A simple caching mechanism """

    def __init__(self,dirname):
        """
        Setup the object
        @param self
        @param string dirname name of the cache directory
        """
        try: self.encoding = encoding
        except: self.encoding = 'utf-8'
        self.dirname = dirname
        if not os.path.isdir(dirname):
            splitted = dirname.split(os.sep)
            temp = ""
            for path_element in splitted: # loop through path components, making directories as needed
                temp += path_element + os.sep
                if os.access(temp, os.F_OK) == 1:
                    continue
                else:
                    os.mkdir(temp)

    def makename(self,fname,ctype):
        """
        Setup cache file name
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @return string cname cache file name
        """
        return os.path.join( self.dirname, fname.replace(os.sep,'%2f') + '.' + ctype )

    def check(self,fname,ctype,ftim=0):
        """
        Check whether the copy in cache is up-to-date
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @param optional float ftim time to check the cache against. If 0 (default),
               check runs against the file specified by fname. Otherwise, the fname
               file itself will be ignored, and cache checked using ftim. So ftim
               should correspond to what os.path.getmtime() would have returned.
        @return boolean up2date
        """
        if ftim==0 and not os.path.isfile(fname): return False # no origin
        if not os.path.isdir(self.dirname): return False # no cache dir
        cname = self.makename(fname,ctype)
        if not os.path.isfile(cname): return False # no cache
        if os.path.getsize(cname) == 0: return False # no content
        if ftim==0: ftim = os.path.getmtime(fname)
        if ftim > os.path.getmtime(cname): # expired
            os.unlink(cname)
            return False
        return True

    def get(self,fname,ctype):
        """
        Get the string from cache content for a given file
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @return string content (empty string if none)
        """
        cname = self.makename(fname,ctype)
        if not os.path.isfile(cname): return '' # no cache
        cfile = fopen(cname,'r','zip')
        cont  = cfile.read().decode(self.encoding)
        cfile.close()
        return cont

    def getObj(self,fname,ctype,ftim):
        """
        Get the object from cache content for a given file. Uses cPickle
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @return obj content or False if not found in cache
        """
        cname = self.makename(fname,ctype)
        if not os.path.isfile(cname): return False # no cache
        cfile = open(cname,'r')
        cont  = cPickle.load(cfile)
        cfile.close()
        return cont

    def put(self,fname,ctype,content):
        """
        Save content to cache
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @param string content
        """
        cname = self.makename(fname,ctype)
        cfile = fopen(cname,'w','zip')
        cont = content.encode(self.encoding)
        cfile.write( cont )
        cfile.close()

    def putObj(self,fname,ctype,obj):
        """
        Save object to cache using cPickle
        @param self
        @param string fname name of the original file
        @param string ctype type of the cached part
        @param object obj
        """
        cname = self.makename(fname,ctype)
        cfile = open(cname,'w')
        cPickle.dump(obj,cfile,cPickle.HIGHEST_PROTOCOL)
        cfile.close()

    def clear(self):
        """ Remove all cached content """
        for fname in listdir(self.dirname): os.unlink(fname)

