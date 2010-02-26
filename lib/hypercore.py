"""
$Id$
HyperSQL Core elements
Copyright 2001 El Paso Energy, Inc.  All Rights Reserved
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from hyperjdoc import JavaDoc, PackageTaskList

class ElemInfo:
    """ Object to hold information about a view, function, or procedure """
    def __init__(self):
        self.name = ""
        self.lineNumber = -1
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.javadoc = JavaDoc()

class PackageInfo:
    """ Object to hold information about a package """
    def __init__(self):
        self.packageName = ""
        self.lineNumber = -1
        self.functionInfoList = []
        self.procedureInfoList = []
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.javadoc = JavaDoc()
        self.bugs = PackageTaskList()
        self.todo = PackageTaskList()

class FileInfo:
    """ Object to hold information about a file """
    def __init__(self):
        self.fileName = ""
        self.fileType = "" # cpp files are only scanned for sql "where used" information
        self.viewInfoList = []
        self.packageInfoList = []
        self.uniqueNumber = 0 # used to create unique file name for where used list


class MetaInfo:
    """ Object to hold global information (e.g. configuration options) """
    def __init__(self):
        self.fileInfoList = []
        self.fileWithPathnamesIndex_FileName = ""
        self.fileNoPathnamesIndex_FileName = ""
        self.viewIndex_FileName = ""
        self.packageIndex_FileName = ""
        self.functionIndex_FileName = ""
        self.procedureIndex_FileName = ""
        self.packageFuncProdIndex_FileName = ""
        self.scriptName = ""
        self.htmlDir = ""
        self.versionString = ""
        self.indexForWhereUsedFiles = 0
        
    def NextIndex(self):
        """Used to generate unique file names for where used indices"""
        self.indexForWhereUsedFiles += 1
        return self.indexForWhereUsedFiles


def TupleCompareFirstElements(a, b):
    """ used for sorting list of tuples by values of first elements in the tuples"""
    if a[0] < b[0]:
	return -1
    if a[0] > b[0]:
	return 1
    return 0


def CaseInsensitiveComparison(a, b):
    """ used for case insensitive string sorts"""
    if a.upper() < b.upper():
	return -1
    if a.upper() > b.upper():
	return 1
    return 0


