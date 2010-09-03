"""
Parsing the file system
"""
__revision__ = '$Id$'

import os
from hypercore.elements import FileInfo

def getFileList(sdir, fileExts, skipDirs=[]):
    """
    Recursively scans the source directory specified for relevant files according
    to the file extensions passed by the second parameter, while excluding files/
    directories given with the third (useful to exclude '.svn' and the like)
    Information for matching files will be returned as a list of FileInfo objects.
    @param string dir directory to scan
    @param list fileExts file extensions to consider. Each element must be a tuple
           (str fileType, list extensions)
    @param list skipDirs files/directories to skip
    @return list fileInfoList list of FileInfo objects
    """
    if fileExts is None or len(fileExts)<1: return []

    # get a list of this directory's contents
    # these items are relative and not absolute
    names        = os.listdir(sdir)
    fileInfoList = []

    # setup supported file extensions
    exts = []
    for ext in fileExts: exts += ext[1]

    # iterate through the file list
    for i in names: 

      if i in skipDirs: # do not look in RCS/CVS/SVN/... special dirs
        continue

      # convert from relative to absolute addressing
      # to allow recursive calls
      f1=os.path.join(sdir, i)

      # if this item is also a directory, recurse it too
      if os.path.isdir(f1):
        fileInfoList += getFileList(f1, fileExts, skipDirs)

      else:  # file found, only add specific file extensions to the list
        fspl = f1.split('.')
        ext  = fspl[len(fspl)-1]
        if ext in exts:
          temp = FileInfo()
          temp.fileName = f1
          for ftype in fileExts:
            if ext in ftype[1]:
              temp.fileType = ftype[0]
              break
          fileInfoList.append(temp)
    return fileInfoList

