"""
$Id$
HyperSQL Core elements
Copyright 2001 El Paso Energy, Inc.  All Rights Reserved
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from hyperjdoc import JavaDoc, PackageTaskList

class ElemInfo(object):
    """ Object to hold information about a view, function, or procedure """
    def __init__(self):
        """ Initialize the object with useful defaults """
        self.name = ""
        self.lineNumber = -1
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.paramCount = 0
        self.javadoc = JavaDoc()

class PackageInfo(ElemInfo):
    """ Object to hold information about a package """
    def __init__(self):
        """ Initialize the object with useful defaults """
        ElemInfo.__init__(self)
        self.functionInfoList = []
        self.procedureInfoList = []
        self.bugs = PackageTaskList()
        self.todo = PackageTaskList()
        self.verification = {}
        self.verification = PackageTaskList()

class FileInfo:
    """ Object to hold information about a file """
    def __init__(self):
        """ Initialize the object with useful defaults """
        self.fileName = ""
        self.fileType = "" # cpp files are only scanned for sql "where used" information
        self.viewInfoList = []
        self.packageInfoList = []
        self.uniqueNumber = 0 # used to create unique file name for where used list


class MetaInfo:
    """ Object to hold global information (e.g. configuration options) """
    def __init__(self):
        """ Initialize the object with useful defaults """
        self.fileInfoList = []
        self.scriptName = ""
        self.htmlDir = ""
        self.versionString = ""
        self.indexForWhereUsedFiles = 0
        self.linesOfCode = {}
        self.linesOfCode['totals'] = 0
        self.linesOfCode['code'] = 0
        self.linesOfCode['comment'] = 0
        self.linesOfCode['empty'] = 0
        
    def NextIndex(self):
        """
        Used to generate unique file names for where used indices
        @return int unique number
        """
        self.indexForWhereUsedFiles += 1
        return self.indexForWhereUsedFiles

    def incLoc(self,what,incBy=1):
        """
        Increase the number of 'lines of code' for the given type
        @param self
        @param string type ('totals','code','comment','empty')
        @param optional int incBy increment by this value (default: 1)
        """
        if what not in ['totals','code','comment','empty']:
            return
        self.linesOfCode[what] += incBy

    def getLoc(self,what):
        """
        Return the number of 'lines of code' for the given type
        @param self
        @param string type ('totals','code','comment','empty')
        @return int loc lines of code for the given type
        """
        if what not in ['totals','code','comment','empty']:
            return
        return self.linesOfCode[what]


def TupleCompareFirstElements(a, b):
    """
    used for sorting list of tuples by values of first elements in the tuples
    @param tuple a
    @param tuple b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a[0] < b[0]:
	return -1
    if a[0] > b[0]:
	return 1
    return 0


def CaseInsensitiveComparison(a, b):
    """
    used for case insensitive string sorts
    @param string a
    @param string b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a.upper() < b.upper():
	return -1
    if a.upper() > b.upper():
	return 1
    return 0


