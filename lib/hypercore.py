"""
$Id$
HyperSQL Core elements
Copyright 2001 El Paso Energy, Inc.  All Rights Reserved
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from hyperjdoc import JavaDoc, PackageTaskList
from locale import format as loc_format, setlocale, LC_NUMERIC
import re # for eatStrings

try:
    setlocale(LC_NUMERIC, '')
except:
    None


class ElemInfo(object):
    """ Object to hold information about a function, or procedure """
    def __init__(self):
        """ Initialize the object with useful defaults """
        self.name = ""
        self.lineNumber = -1
        self.whatUsed = {} # file name key, fileInfo and line number list
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.paramCount = 0
        self.javadoc = JavaDoc()
    def __repr__(self):
        """ Basic information for simple debug """
        if self.lineNumber<0: return 'Empty ElemInfo object'
        if self.name: ret = 'ElemInfo object "' + self.name + '"'
        else: ret = 'unnamed ElemInfo object'
        if self.parent: ret += ' with parent ' + `self.parent`
        else: ret += ' without parent'
        return ret + ', attached JavaDoc:\n' + `self.javadoc`

class StandAloneElemInfo(ElemInfo):
    """ Object to hold information about stand-alone elements (tables, views, etc.) """
    def __init__(self):
        """ Initialize the object with useful defaults """
        ElemInfo.__init__(self)
        self.bugs = PackageTaskList()
        self.todo = PackageTaskList()
        self.verification = PackageTaskList()

class PackageInfo(StandAloneElemInfo):
    """ Object to hold information about a package """
    def __init__(self):
        """ Initialize the object with useful defaults """
        StandAloneElemInfo.__init__(self)
        self.functionInfoList = []
        self.procedureInfoList = []

class FormInfo(StandAloneElemInfo):
    """ Object to hold information about an Oracle Form """
    def __init__(self):
        """ Initialize the object with useful defaults """
        StandAloneElemInfo.__init__(self)
        self.formType = ''
        self.title = ''
        self.objects = 0
        self.stats = {}
        self.packageInfoList = []
        self.triggerInfoList = []
        self.functionInfoList = []
        self.procedureInfoList = []
    def __repr__(self):
        """ Basic information for debug """
        if self.formType == '': return 'empty form'
        ret = 'Form '+self.formType+' "'+self.name+'":\n' \
            + '* '+`self.objects`+' objects\n' \
            + '* '+`len(self.packageInfoList)`+' packages\n' \
            + '* '+`len(self.functionInfoList)`+' functions\n' \
            + '* '+`len(self.procedureInfoList)`+' procedures\n' \
            + '* '+`len(self.triggerInfoList)`+' trigger\n' \
            + '* Stats: '+`self.stats`+'\n'
        if self.parent: ret += '* Parent: '+self.parent.fileName
        return ret

def listCompName(a,b):
    """
    Helper to sort a list of objects by their "name" property using
    list.sort(listCompName)
    used by FileInfo.sortLists
    """
    if a.name < b.name: return -1
    elif a.name > b.name: return 1
    else: return 0

class FileInfo(object):
    """ Object to hold information about a file """
    def __init__(self):
        """ Initialize the object with useful defaults """
        self.fileName = ""
        self.fileType = "" # cpp files are only scanned for sql "where used" information
        self.viewInfoList = []
        self.mviewInfoList = []
        self.tabInfoList = []
        self.synInfoList = []
        self.seqInfoList = []
        self.packageInfoList = []
        self.functionInfoList = []
        self.procedureInfoList = []
        self.triggerInfoList = []
        self.formInfoList = []
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.lines = 0
        self.bytes = 0

    def sortLists(self):
        """ Sort all lists alphabetically by object name """
        if len(self.viewInfoList) > 0: self.viewInfoList.sort(listCompName)
        if len(self.packageInfoList) > 0:
            for p in self.packageInfoList:
                if len(p.functionInfoList) > 0: p.functionInfoList.sort(listCompName)
                if len(p.procedureInfoList) > 0: p.procedureInfoList.sort(listCompName)

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
        self.depGraph = {}
        self.depGraph['file2file'] = []
        self.depGraph['file2object'] = []
        self.depGraph['object2file'] = []
        self.depGraph['object2object'] = []
        self.colors = {}

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
        @param string type ('totals','code','comment','empty','mixed')
        @return int loc lines of code for the given type
        """
        if what not in ['totals','code','comment','empty','mixed']:
            return 0
        if what == 'mixed':
            return self.getLoc('totals') - self.getLoc('code') - self.getLoc('comment') - self.getLoc('empty')
        return self.linesOfCode[what]

    def getLocPct(self,what,decs=2):
        """
        Return the percentage of 'lines of code' for the given type
        @param self
        @param string type ('totals','code','comment','empty','mixed')
        @param optional int decs round the value to how many decimals? Default: 2
        @return float loc percentage of lines of code for the given type
        """
        if what not in ['totals','code','comment','empty','mixed']:
            return 0.0
        if self.getLoc('totals') != 0: return round( (float(self.getLoc(what)) / self.getLoc('totals')) * 100, decs)
        else: return round(0,decs)

    def getFileStat(self,what):
        """
        Return some file statistics
        @param self
        @param string type ('files','avg lines','min lines','max lines',
               'sum bytes','avg bytes','min bytes','max bytes')
        @return number stat_value value for the requested stat. Depending on its
                type, this may be either an integer or a float
        """
        if what not in ['files','avg lines','min lines','max lines','sum bytes','avg bytes','min bytes','max bytes']:
            return 0
        fileCount = len(self.fileInfoList)
        if what in ['sum bytes','avg bytes','min bytes','max bytes']:
            sumBytes = 0
            if len(self.fileInfoList) > 0:
                minBytes = self.fileInfoList[0].bytes
                maxBytes = self.fileInfoList[0].bytes
            else:
                minBytes = 0
                maxBytes = 0
            for file in self.fileInfoList:
                sumBytes += file.bytes
                if file.bytes < minBytes:
                    minBytes = file.bytes
                elif file.bytes > maxBytes:
                    maxBytes = file.bytes
        if what in ['min lines','max lines']:
            if len(self.fileInfoList) > 0:
                minLines = self.fileInfoList[0].lines
                maxLines = self.fileInfoList[0].lines
            else:
                minLines = 0
                maxLines = 0
            for file in self.fileInfoList:
                if file.lines < minLines:
                    minLines = file.lines
                elif file.lines > maxLines:
                    maxLines = file.lines
        if what == 'files':
            return fileCount
        elif what == 'avg lines':
            return self.getLoc('totals') / fileCount
        elif what == 'min lines':
            return minLines
        elif what == 'max lines':
            return maxLines
        elif what == 'sum bytes':
            return sumBytes
        elif what == 'avg bytes':
            return float(sumBytes/fileCount)
        elif what == 'min bytes':
            return minBytes
        elif what == 'max bytes':
            return maxBytes

    def getFileSizeStat(self,boundary):
        """
        Obtain some size statistics
        @param self
        @param list boundary size groups you want to split the stats into
        @return dict stats
        """
        sumBytes = self.getFileStat('sum bytes')
        fileCount = len(self.fileInfoList)
        boundary.sort()
        stat = {}
        for limit in boundary:
            stat[limit] = 0
        for file in self.fileInfoList:
            for limit in boundary:
                if file.bytes < limit:
                    stat[limit] += 1
                    break
        return stat

    def getFileLineStat(self,boundary):
        """
        Obtain some line statistics
        @param self
        @param list boundary size groups you want to split the stats into
        @return dict stats
        """
        sumLines = self.getLoc('totals')
        fileCount = len(self.fileInfoList)
        boundary.sort()
        stat = {}
        for limit in boundary:
            stat[limit] = 0
        for file in self.fileInfoList:
            for limit in boundary:
                if file.lines < limit:
                    stat[limit] += 1
                    break
        return stat


def TupleCompareFirstElements(a, b):
    """
    used for sorting list of tuples by values of first elements in the tuples
    @param tuple a
    @param tuple b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a[0] < b[0]: return -1
    if a[0] > b[0]: return 1
    return 0


def CaseInsensitiveComparison(a, b):
    """
    used for case insensitive string sorts
    @param string a
    @param string b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a.upper() < b.upper(): return -1
    if a.upper() > b.upper(): return 1
    return 0

def num_format(num, places=0):
    return loc_format("%.*f", (places, num), True)

def size_format(size,decs=2):
    suffixes = [("B",2**10), ("K",2**20), ("M",2**30), ("G",2**40), ("T",2**50)]
    for suf, lim in suffixes:
        if size > lim:
            continue
        else:
            return num_format( round(size/float(lim/2**10),decs), decs )+suf

def eatStrings(text):
    """
    eat (single-quoted) string contents and return remaining text
    @param string text text to parse
    @return string text text with strings removed
    @return boolean matched_string whether any strings where encountered
    """
    strpatt = re.compile("('[^']*')+")    # String-Regexp
    result = strpatt.search(text)
    matched_string = False
    while result != None:
        matched_string = True
        for g in range(len(result.groups())):
            text = text.replace(result.group(g) , "")
        result = strpatt.search(text)
    return text, matched_string
