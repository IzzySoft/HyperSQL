"""
$Id$
HyperSQL simple Cache
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

import os
import cPickle
from iz_tools.system import fopen

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

    def getOName(self,cname,ctype):
        """
        Get the name of the original file a cache file belongs to (counter-part to makename)
        @param self
        @param strinc cname filename of the cache file
        @return string fname filename of the original file
        """
        #return cname[len(self.dirname):-len(ctype)-1].replace('%2f',os.sep)
        return cname[0:-len(ctype)-1].replace('%2f',os.sep)

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

    def removeObsolete(self,basedir=''):
        """
        Cleanup files from cache which do no longer exist in the original location
        (i.e. which have been deleted/moved, so they would no longer match)
        @param self
        @param optional string basedir   base directory of original codebase
        @return int removed              how many files have been removed
        """
        if not os.path.isdir(self.dirname): return 0 # no cache dir
        names=os.listdir(self.dirname)
        dc = 0
        for i in names:
            splitted = i.split('.')
            ctype = splitted[len(splitted)-1]
            if not ctype in ['code','formcode']: continue
            if not os.path.isfile(self.getOName(i,ctype)):
                os.unlink( os.path.join(self.dirname, i) )
                dc += 1
        return dc
            

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

    def clear(self,ctype='all'):
        """
        Remove cached content
        @param self
        @param optional ctype type (extension) of cache to remove (default: 'all')
        """
        if ctype=='all':
            for fname in os.listdir(self.dirname): os.unlink(fname)
        else:
            ext = '.'+ctype
            pos = len(ext)
            for fname in os.listdir(self.dirname):
                if fname[len(fname)-pos:]==ext: os.unlink(os.path.join(self.dirname,fname))

