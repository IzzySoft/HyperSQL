#!/usr/bin/python

# see main function at bottom of file

"""
    Version 1.0 written by Randy Phillips September 2001
    Copyright 2001 El Paso Energy, Inc.  All Rights Reserved

    Version 1.1+ written by Itzchak Rehberg
    Copyright 2010 Itzchak Rehberg & IzzySoft

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    Author contact information: randy-san@users.sourceforge.net
"""

import os, sys, string, time, ConfigParser, fileinput
from cgi import escape
from shutil import copy2

class JavaDoc:
    """Object to hold details from javadoc style comments"""
    def __init__(self):
        self.lineNumber = -1
        self.lines = 0
        self.name = ''
        self.objectType = ''
        self.params = []
        self.retVals = []
        self.desc = ''
        self.version = ''
        self.author = ''
        self.info = ''
        self.example = ''
        self.todo = ''
        self.bug = ''
        self.copyright = ''
        self.deprecated = ''
        self.private = False
        self.see = ''
        self.webpage = ''
        self.license = ''
    def isDefault(self):
        """Check if this is just an empty dummy (True), or if any real data have been assigned (False)"""
        if self.lineNumber != -1: return False
        return True

class JavaDocParam:
    """Parameters passed to a function/Procedure. Used by JavaDoc.params and JavaDoc.retVals"""
    def __init__(self):
        self.inout = 'in' # 'in', 'out', or 'inout'. Ignored for retVals
        self.sqltype = 'VARCHAR2'
        self.default = ''
        self.desc = ''
        self.name = ''

class ViewInfo:
    """ Object to hold information about a view """
    def __init__(self):
        self.viewName = ""
        self.lineNumber = -1
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.javadoc = JavaDoc()

class FunctionInfo:
    """ Object to hold information about a function """
    def __init__(self):
        self.functionName = ""
        self.lineNumber = -1
        self.whereUsed = {} # file name key, fileInfo and line number list
        self.uniqueNumber = 0 # used to create unique file name for where used list
        self.parent = None
        self.javadoc = JavaDoc()

class ProcedureInfo:
    """ Object to hold information about a procedure """
    def __init__(self):
        self.procedureName = ""
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
        self.toDoList = ""
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


def FindFilesAndBuildFileList(dir, fileInfoList, meta_info):
    """
    Recursively scans the source directory specified (1st param) for
    relevant files according to the file extensions configured in meta_info
    (3rd param), while excluding RCS directories (such as 'RCS', 'CVS', and
    '.svn'). Information for matching files is stored in fileInfoList (2nd param).
    """

    # get a list of this directory's contents
    # these items are relative and not absolute
    names=os.listdir(dir)

    # iterate through the file list
    for i in names: 

      if i in meta_info.rcsnames: # do not look in RCS/CVS/SVN/... special dirs
	    continue

      # convert from relative to absolute addressing
      # to allow recursive calls
      f1=os.path.join(dir, i)

      # if this item is also a directory, recurse it too
      if os.path.isdir(f1):
        FindFilesAndBuildFileList(f1, fileInfoList, meta_info)
	    
      else:  # file found, only add specific file extensions to the list
        fspl = f1.split('.')
        ext  = fspl[len(fspl)-1]
        if ext in meta_info.sql_file_exts:
          temp = FileInfo()
          temp.fileName = f1
          temp.fileType = "sql"
          if temp.uniqueNumber == 0:
            temp.uniqueNumber = meta_info.NextIndex()
          fileInfoList.append(temp)
        if ext in meta_info.cpp_file_exts:
          temp = FileInfo()
          temp.fileName = f1
          temp.fileType = "cpp"
          if temp.uniqueNumber == 0:
            temp.uniqueNumber = meta_info.NextIndex()
          fileInfoList.append(temp)

def ScanJavaDoc(text,lineno=0):
    """
    Scans the text array (param 1) for the javadoc style comments starting at
    line lineno (param 2). Called from ScanFilesForViewsAndPackages.
    Returns a list of instances of the JavaDoc class - one instance per javadoc
    comment block.
    """
    elem = 'desc'
    res  = []
    opened = False
    otypes = ['function', 'procedure', 'view', 'pkg'] # supported object types
    tags   = ['param', 'return', 'version', 'author', 'info', 'example',
              'todo', 'bug', 'copyright', 'deprecated', 'private',
              'see', 'webpage', 'license'] # other supported tags
    for lineNumber in range(lineno,len(text)):
      line = text[lineNumber].strip()
      if not opened and line[0:3] != '/**':
        continue
      if line[0:1] == '*' and line[0:2] != '*/':
        line = line[1:].strip()
      if line == '*/':
        res.append(item)
        elem = 'desc'
        opened = False
        continue
      if elem == 'desc':
        if line[0:3] == '/**':
          opened = True
          item = JavaDoc()
          item.lineNumber = lineNumber
          item.desc += line[3:].strip()
          continue
        if line[0:1] != '@':
          if line[len(line)-2:] == '*/':
            item.desc += line[0:len(line)-2]
            res.append(item)
            opened = False
            elem = 'desc'
            continue
          else:
            item.desc += ' ' + line
            continue
        else:
          elem = ''
      if elem == '':
        if line[0:1] != '@': # unexpected and unsupported
          continue
        doc = line.split()
        tag = doc[0][1:]
        if tag in otypes: # line describes supported object type + name
          item.objectType = doc[0][1:]
          item.name = doc[1]
        elif tag in tags: # other supported tag
          if tag == 'param':    # @param inout type [name [desc]]
            p = JavaDocParam()
            if doc[1] in ['in','out','inout']:
              p.inout   = doc[1].upper()
              p.sqltype = doc[2].upper()
              if len(doc) > 3:
                p.name = doc[3]
                for w in range(4,len(doc)):
                  p.desc += doc[w] + ' '
                p.desc = p.desc.strip()
            else:
              p.sqltype = doc[1]
              if len(doc) > 2:
                p.name = doc[2]
                for w in range(3,len(doc)):
                  p.desc += doc[w] + ' '
                p.desc = p.desc.strip()
            item.params.append(p)
          elif tag == 'return': # @return type [name [desc]
            p = JavaDocParam()
            p.sqltype = doc[1].upper()
            if len(doc)>2:
              p.name = doc[2]
              for w in range(3,len(doc)):
                p.desc += doc[w] + ' '
            item.retVals.append(p)
          elif tag == 'version':
            item.version = line[len(tag)+1:].strip()
          elif tag == 'author':
            item.author = line[len(tag)+1:].strip()
          elif tag == 'info':
            item.info = line[len(tag)+1:].strip()
          elif tag == 'example':
            item.example = line[len(tag)+1:].strip()
          elif tag == 'todo':
            item.todo = line[len(tag)+1:].strip()
          elif tag == 'bug':
            item.bug = line[len(tag)+1:].strip()
          elif tag == 'copyright':
            item.copyright = line[len(tag)+1:].strip()
          elif tag == 'deprecated':
            item.deprecated = line[len(tag)+1:].strip()
          elif tag == 'private':
            item.private = True
          elif tag == 'see':
            item.see = line[len(tag)+1:].strip()
          elif tag == 'webpage':
            item.webpage = line[len(tag)+1:].strip()
          elif tag == 'license':
            item.license = line[len(tag)+1:].strip()
        else:             # unsupported tag, ignore
          continue
        
    return res

def JavaDocShortDesc(desc):
    """
    Generate a short desc from the given desc
    Truncates after the first occurence of ".;\n" - whichever from this
    characters comes first
    """
    dot = []
    if desc.find('.')>0:
      dot.append( desc.find('.') )
    if desc.find(';')>0:
      dot.append( desc.find(';') )
    if desc.find('\n')>0:
      dot.append( desc.find('\n') )
    if len(dot)>0:
      cut = min(dot)
      return desc[0:cut]
    else:
      return desc

def JavaDocApiElem(jdoc,unum):
    """
    Generates HTML block from JavaDoc Api Info for the element passed
    Param: instance of JavaDoc class, int unique number
    """
    html = '<A NAME="'+jdoc.name+'_'+str(unum)+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom:10px" WIDTH="95%" ALIGN="center"><TR><TH>' + jdoc.name + '</TH>\n'
    html += '<TR><TD>\n';
    if jdoc.desc != '':
      html += '  <DIV CLASS="jd_desc">' + jdoc.desc + '</DIV>\n'
    html += '  <DL>'
    if jdoc.objectType in ['function', 'procedure']:
      if jdoc.private:
        html += ' <DT>Private</DT><DD>Just used internally.</DD>'
      html += '  <DT>Syntax:</DT><DD><DIV STYLE="margin-left:15px;text-indent:-15px;">' + jdoc.name + ' ('
      for p in range(len(jdoc.params)):
        html += jdoc.params[p].name + ' ' + jdoc.params[p].inout + ' ' + jdoc.params[p].sqltype
        if p<len(jdoc.params)-1:
          html += ', '
      html += ')</DIV></DD>\n'
      if len(jdoc.params) > 0:
        html += ' <DT>Parameters:</DT><DD>'
        for p in range(len(jdoc.params)):
          html += '<DIV STYLE="margin-left:15px;text-indent:-15px;">' + jdoc.params[p].inout + ' ' + jdoc.params[p].sqltype + ' <B>' + jdoc.params[p].name + '</B>'
          if jdoc.params[p].desc != '':
            html += ': ' + jdoc.params[p].desc
          html += '</DIV>'
        html += '</DD>\n'
      if jdoc.objectType == 'function':
        html += ' <DT>Return values:</DT><DD><UL STYLE="list-style-type:none;margin-left:-40px;">'
        for p in range(len(jdoc.retVals)):
          html += '<LI>' + jdoc.retVals[p].sqltype + ' <B>' + jdoc.retVals[p].name + '</B>'
          if jdoc.retVals[p].desc != '':
            html += ': ' + jdoc.retVals[p].desc
          html += '</LI>'
        html += '</UL></DD>\n'
    if jdoc.example != '':
      html += '<DT>Example Usage:</DT><DD>' + jdoc.example + '</DD>'
    if jdoc.author != '':
      html += '<DT>Author:</DT><DD>' + jdoc.author + '</DD>'
    if jdoc.copyright != '':
      html += '<DT>Copyright:</DT><DD>' + jdoc.copyright + '</DD>'
    if jdoc.license != '':
      html += '<DT>License:</DT><DD>' + jdoc.license + '</DD>'
    if jdoc.webpage != '':
      html += '<DT>Webpage:</DT><DD><A HREF="' + jdoc.webpage + '">' + jdoc.webpage + '</A></DD>'
    if jdoc.bug != '':
      html += '<DT>BUG:</DT><DD>' + jdoc.bug + '</DD>'
    if jdoc.deprecated != '':
      html += '<DT>DEPRECATED:</DT><DD>' + jdoc.deprecated + '</DD>'
    if jdoc.version != '':
      html += '<DT>Version Info:</DT><DD>' + jdoc.version + '</DD>'
    if jdoc.info != '':
      html += '<DT>Additional Info:</DT><DD>' + jdoc.info + '</DD>'
    if jdoc.see != '':
      html += '<DT>See also:</DT><DD>' + jdoc.see + '</DD>'
    if jdoc.todo != '':
      html += '<DT>TODO:</DT><DD>' + jdoc.todo + '</DD>'
    html += '\n</DL></TD></TR></TABLE>\n'
    return html

def ScanFilesForViewsAndPackages(meta_info):
    """
    Scans files from meta_info.fileInfoList for views and packages and collects
    some metadata about them (name, file, lineno). When encountering a package
    spec, it also scans for its functions and procedures.
    It simply searches the source file for keywords. With each object info,
    file name and line number are stored (and can be used to identify parent
    and children) - for functions and procedures contained in packages, a link
    to their parent is stored along.
    """

    fileInfoList = meta_info.fileInfoList

    # first, find views in files
    dot_count = 1
    for file_info in fileInfoList:

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue
        
	# print a . every file
	sys.stdout.write(".")
	sys.stdout.flush()
	if (dot_count % 60) == 0: # carriage return every 60 dots
	    print
	    sys.stdout.flush()

	dot_count += 1
	infile = open(file_info.fileName, "r")
	fileLines = infile.readlines()
	infile.close()

	# scan this file for possible JavaDoc style comments
	jdoc = ScanJavaDoc(fileLines)

	# if we find a package definition, this flag tells us to also look for
	# functions and procedures.  If we don't find a package definition, there
	# is no reason to look for them
	package_count = -1

	for lineNumber in range(len(fileLines)):

	    token_list = fileLines[lineNumber].split()

	    # ignore very short lines
	    if len(token_list) < 2:
		continue

	    # ignore lines that begin with comments
	    if token_list[0][:2] == "--" or token_list[0][:2] == "//" or token_list[0][:2] == "##":
		continue

	    # find views.  Loop through looking for the different styles of view definition
	    for token_index in range(len(token_list)):
		# look for CREATE VIEW, REPLACE VIEW, FORCE VIEW, making sure enough tokens exist
		if len(token_list) > token_index+1 \
		and token_list[token_index+1].upper() == "VIEW" \
		and (token_list[token_index].upper() == "CREATE" \
		    or token_list[token_index].upper() == "REPLACE" \
		    or token_list[token_index].upper() == "FORCE"):
		    view_info = ViewInfo()
                    view_info.parent = file_info
		    view_info.viewName = token_list[token_index+2]
		    view_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(view_info.viewName,jdoc[j].name)==0 and jdoc[j].objectType=='view') or (ln>0 and ln<4):
                        view_info.javadoc = jdoc[j]
		    file_info.viewInfoList.append(view_info)

	    # find package definitions - set flag if found
	    # look for PACKAGE BODY x, making sure enough tokens exist
	    for token_index in range(len(token_list)):
		if len(token_list) > token_index+2 \
		and token_list[token_index].upper() == "PACKAGE" \
		and token_list[token_index+1].upper() == "BODY":
		    package_info = PackageInfo()
                    package_info.parent = file_info
		    package_info.packageName = token_list[token_index+2]
		    package_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(package_info.packageName,jdoc[j].name)==0 and jdoc[j].objectType=='package') or (ln>0 and ln<4):
                        package_info.javadoc = jdoc[j]
		    file_info.packageInfoList.append(package_info) # permanent storage
		    package_count += 1 # use this flag below
		    
	    # if a package definition was found, look for functions and procedures
	    if package_count != -1:
		# first find functions
		if len(token_list) > 1 and token_list[0].upper() == "FUNCTION":
		    function_name = token_list[1].split('(')[0] # some are "name(" and some are "name ("
		    function_info = FunctionInfo()
                    function_info.parent = file_info.packageInfoList[package_count]
		    function_info.functionName = function_name
		    function_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(function_name,jdoc[j].name)==0 and jdoc[j].objectType=='function') or (ln>0 and ln<4):
                        function_info.javadoc = jdoc[j]
		    file_info.packageInfoList[package_count].functionInfoList.append(function_info)
		    
		# now find procedures
		if len(token_list) > 1 and token_list[0] == "PROCEDURE":
		    procedure_name = token_list[1].split('(')[0] # some are "name(" and some are "name ("
		    procedure_info = ProcedureInfo()
                    procedure_info.parent = file_info.packageInfoList[package_count]
		    procedure_info.procedureName = procedure_name
		    procedure_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(procedure_name,jdoc[j].name)==0 and jdoc[j].objectType=='procedure') or (ln>0 and ln<4):
                        procedure_info.javadoc = jdoc[j]
		    file_info.packageInfoList[package_count].procedureInfoList.append(procedure_info)

    # print carriage return after last dot
    print


def ScanFilesForWhereViewsAndPackagesAreUsed(meta_info):
    """
    Scans files collected in meta_info.fileInfoList and checks them line by line
    with meta_info.<object>list for calls to those objects. If it finds any, it
    updates <object>list where_used property accordingly.
    """

    fileInfoList = meta_info.fileInfoList

    outerfileInfoList = []
    for file_info in fileInfoList:
        outerfileInfoList.append(file_info)

    dot_count = 1
    for outer_file_info in outerfileInfoList:
        # print a . every file
        sys.stdout.write(".")
        sys.stdout.flush()
        if (dot_count % 60) == 0: # carriage return every 60 dots
            print
            sys.stdout.flush()
        dot_count += 1

        infile = open(outer_file_info.fileName, "r")
        fileLines = infile.readlines()
        infile.close()

        # if we find a package definition, this flag tells us to also look for
        # functions and procedures.  If we don't find a package definition, there
        # is no reason to look for them
        package_count = -1

        for lineNumber in range(len(fileLines)):

            token_list = fileLines[lineNumber].split()

            # ignore very short lines - commented out, since otherwise some where_useds are not found
            #if len(token_list) < 2:
            #    print 'SKIPPED: ' + fileLines[lineNumber]
            #    continue

            # ignore lines that begin with comments
            if len(token_list) > 0:
                if token_list[0][:2] == "--" or token_list[0][:2] == "//" or token_list[0][:2] == "##":
                    continue

            # usage only, no creates, replace, force views packages functions or procedures
            usage_flag = 1
            for token_index in range(len(token_list)):

                # look for CREATE VIEW, REPLACE VIEW, FORCE VIEW, making sure enough tokens exist
                if len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "VIEW" \
                and (token_list[token_index].upper() == "CREATE" \
                    or token_list[token_index].upper() == "REPLACE" \
                    or token_list[token_index].upper() == "FORCE"):
                    # we are creating, forcing, or replacing - not using.  Set flag to 0
                    usage_flag = 0

                # look for PACKAGE BODY x IS, making sure enough tokens exist
                if token_list[token_index].upper() == "PACKAGE" \
                and len(token_list) > token_index+2 \
                and token_list[token_index+1].upper() == "BODY":
                    package_count += 1 # set flag
                    usage_flag = 0

                # if a package definition was found, look for functions and procedures
                if package_count != -1:
                    # first find functions
                    if token_list[0] == "FUNCTION" and len(token_list) > 1:
                        usage_flag = 0
                    # now find procedures
                    if token_list[0] == "PROCEDURE" and len(token_list) > 1:
                        usage_flag = 0

            if usage_flag == 0:
                continue

            # Loop through all previously found views and packages to see if they are used in this line of text
            for inner_file_info in fileInfoList:

                # if this FileInfo instance has views
                if len(inner_file_info.viewInfoList) != 0:
                    for view_info in inner_file_info.viewInfoList:
                        # perform case insensitive find
                        if fileLines[lineNumber].upper().find(view_info.viewName.upper()) != -1:
                            if outer_file_info.fileName not in view_info.whereUsed.keys():
                                view_info.whereUsed[outer_file_info.fileName] = []
                                view_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                            else:
                                view_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                            # generate a unique number for use in making where used file if needed
                            if view_info.uniqueNumber == 0:
                                view_info.uniqueNumber = meta_info.NextIndex()


                # if this FileInfo instance has packages
                if len(inner_file_info.packageInfoList) != 0:
                    for package_info in inner_file_info.packageInfoList:

                        # perform case insensitive find, this is "package name"."function or procedure name"
                        if fileLines[lineNumber].upper().find(package_info.packageName.upper() + ".") != -1:

                            if outer_file_info.fileName not in package_info.whereUsed.keys():
                                package_info.whereUsed[outer_file_info.fileName] = []
                                package_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                            else:
                                package_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                            # generate a unique number for use in making where used file if needed
                            if package_info.uniqueNumber == 0:
                                package_info.uniqueNumber = meta_info.NextIndex()

                            #look for any of this packages' functions
                            for function_info in package_info.functionInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(package_info.packageName.upper() + "." \
                                  + function_info.functionName.upper()) != -1:
                                    if outer_file_info.fileName not in function_info.whereUsed.keys():
                                        function_info.whereUsed[outer_file_info.fileName] = []
                                        function_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                                    else:
                                        function_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                                    # generate a unique number for use in making where used file if needed
                                    if function_info.uniqueNumber == 0:
                                        function_info.uniqueNumber = meta_info.NextIndex()
                            #look for any of this packages procedures
                            for procedure_info in package_info.procedureInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(package_info.packageName.upper() + "." \
                                  + procedure_info.procedureName.upper()) != -1:
                                    if outer_file_info.fileName not in procedure_info.whereUsed.keys():
                                        procedure_info.whereUsed[outer_file_info.fileName] = []
                                        procedure_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                                    else:
                                        procedure_info.whereUsed[outer_file_info.fileName].append((outer_file_info, lineNumber))
                                    # generate a unique number for use in making where used file if needed
                                    if procedure_info.uniqueNumber == 0:
                                        procedure_info.uniqueNumber = meta_info.NextIndex()

    # print carriage return after last dot
    print

def MakeNavBar():
    """Generates HTML code for the general navigation links to all the index pages"""
    s = "<TABLE ID='topbar' WIDTH='98%'><TR>\n"
    s += "  <TD ID='navbar' WIDTH='600px'>\n"
    s += '    <A href="' + metaInfo.packageIndex_FileName + '">Package Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="' + metaInfo.functionIndex_FileName + '">Function Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="' + metaInfo.procedureIndex_FileName + '">Procedure Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="' + metaInfo.packageFuncProdIndex_FileName + '">Full Package Listing</A> &nbsp;&nbsp; \n'
    s += "    <BR>\n"
    s += '    <A href="' + metaInfo.viewIndex_FileName + '">View Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="' + metaInfo.fileNoPathnamesIndex_FileName + '">File Name Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="' + metaInfo.fileWithPathnamesIndex_FileName + '">File Names by Path Index</A> &nbsp;&nbsp; \n'
    s += '    <A href="index.html">Main Index</A> &nbsp;&nbsp; \n'
    s += "  </TD><TD CLASS='title'>\n"
    s += '    ' + metaInfo.title_prefix + '\n'
    s += '  </TD>\n'
    s += '</TR></TABLE>\n'
    return s

def MakeHTMLHeader(meta_info, title_name):
    """Generates common HTML header with menu for all pages"""

    s =  '<html><head>\n'
    s += '  <TITLE>' + metaInfo.title_prefix + ': ' + title_name + '</TITLE>\n'
    s += '  <LINK REL="stylesheet" TYPE="text/css" HREF="' + metaInfo.css_file + '">\n'
    s += '</head><body>\n'
    s += MakeNavBar()
    s += '<HR CLASS="topend">\n'
    return s

def MakeHTMLFooter():
    """Generates common HTML footer for all pages"""
    s = "<HR CLASS='bottomstart'>\n"
    s += "<DIV ID='bottombar'>\n"
    s += MakeNavBar()
    s += "  <DIV ID='generated'>Generated by <A HREF='http://projects.izzysoft.de/trac/hypersql/'>HyperSQL</A> v" + metaInfo.versionString + " at " + time.asctime(time.localtime(time.time())) + "</DIV>";
    s += "</DIV>\n"
    s += "</body></html>"
    return s


def CreateHTMLDirectory(metaInfo):
    """Creates the html directory if needed"""
    splitted = metaInfo.htmlDir.split(os.sep)
    temp = ""
    for path_element in splitted: # loop through path components, making directories as needed
        temp += path_element + os.sep
        if os.access(temp, os.F_OK) == 1:
            continue
        else:
            os.mkdir(temp)


def MakeFileIndexWithPathNames(meta_info):
    """Generate HTML index page for all files, ordered by path names"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.fileWithPathnamesIndex_FileName

    filenametuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
	filenametuplelist.append((file_info.fileName.upper(), file_info))
    filenametuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'File Name by Path Index'))
    outfile.write("<H1>Index Of All Files By Path Name</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'><TR><TD>\n")

    for filenametuple in filenametuplelist:
        file_name = filenametuple[1].fileName
	temp = os.path.split(file_name)[1].replace(".", "_")
	temp += "_" + `filenametuple[1].uniqueNumber` + ".html"
	outfile.write("  <A href=\"" + temp + "\">" + file_name[len(meta_info.topLevelDirectory)+1:])
	outfile.write("</A><BR>\n")

    outfile.write("</TD></TR></TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()
	

def MakeFileIndexNoPathNames(meta_info):
    """Generate HTML index page for all files, ordered by file names, ignoring the path for ordering"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.fileNoPathnamesIndex_FileName

    filenametuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue
	filenametuplelist.append((os.path.split(file_info.fileName)[1].upper(), file_info))
    filenametuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'File Name Index'))
    outfile.write("<H1>Index Of All Files By File Name</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'><TR><TD>\n")

    for filenametuple in filenametuplelist:
        file_name = filenametuple[1].fileName
	temp = os.path.split(file_name)[1].replace(".", "_")
	temp += "_" + `filenametuple[1].uniqueNumber` + ".html"
	outfile.write("  <A href=\"" + temp + "\">" + os.path.split(file_name)[1])
	outfile.write("</A><BR>\n")

    outfile.write("</TD></TR></TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()
	

def MakeViewIndex(meta_info):
    """Generate HTML index page for all views"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.viewIndex_FileName
    top_level_directory = meta_info.topLevelDirectory

    viewtuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
	for view_info in file_info.viewInfoList:
	    viewtuplelist.append((view_info.viewName.upper(), view_info, file_info)) # append as tuple for case insensitive sort

    viewtuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'View Index'))
    outfile.write("<H1>Index Of All Views</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
    outfile.write("  <TR><TH>View</TH><TH>Details</TH><TH>Used</TH></TR>\n")

    for view_tuple in viewtuplelist: # list of tuples describing every view
	# file name and line number as an HTML reference
	HTMLref = os.path.split(view_tuple[2].fileName)[1].replace(".", "_")
	HTMLref += "_" + `view_tuple[2].uniqueNumber` + ".html"
	HTMLref += "#" + `view_tuple[1].lineNumber`
	outfile.write("  <TR><TD><A href=\"" + HTMLref + "\">" + view_tuple[1].viewName.lower() + "</A></TD>")
        outfile.write("<TD>" + JavaDocShortDesc(view_tuple[1].javadoc.desc) + "</TD>")

	if len(view_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `view_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD><A href=\"" + HTMLwhereusedref + "\">where used list</A></TD>")
        else:
            outfile.write("<TD>no use found by HyperSQL</TD>")
        outfile.write("</TR>\n")

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()


def MakePackageIndex(meta_info):
    """Generate HTML index page for all packages"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.packageIndex_FileName
    top_level_directory = meta_info.topLevelDirectory

    packagetuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.packageName.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'Package Index'))
    outfile.write("<H1>Index Of All Packages</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
    outfile.write("  <TR><TH>Package</TH><TH>Details</TH><TH>Used</TH></TR>\n")

    for package_tuple in packagetuplelist: # list of tuples describing every package file name and line number as an HTML reference
        HTMLref = os.path.split(package_tuple[2].fileName)[1].replace(".", "_")
        HTMLref += "_" + `package_tuple[2].uniqueNumber` + ".html"
        if package_tuple[1].javadoc.isDefault():
            HTMLjref = ''
        else:
            HTMLjref = HTMLref + '#' + package_tuple[1].javadoc.name + '_' + `package_tuple[1].uniqueNumber`
        HTMLref += "#" + `package_tuple[1].lineNumber`
        if HTMLjref == '':
            outfile.write("  <TR><TD>" + package_tuple[1].packageName.lower() + " <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        else:
            outfile.write("  <TR><TD><A HREF='" + HTMLjref + "'>" + package_tuple[1].packageName.lower() + "</A> <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        outfile.write("<TD>" + JavaDocShortDesc(package_tuple[1].javadoc.desc) + "</TD>")
        if len(package_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD><A href=\"" + HTMLwhereusedref + "\">where used list</A></TD></TR>\n")
        else:
            outfile.write("<TD>no use found by HyperSQL</TD></TR>\n")

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()


def MakeFunctionIndex(meta_info):
    """Generate HTML index page for all functions"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.functionIndex_FileName
    top_level_directory = meta_info.topLevelDirectory

    functiontuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            for function_info in package_info.functionInfoList:
                functiontuplelist.append((function_info.functionName.upper(), function_info, file_info, package_info)) # append as tuple for case insensitive sort

    functiontuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'Function Index'))
    outfile.write("<H1>Index Of All Functions</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
    outfile.write("  <TR><TH>Function</TH><TH>from Package</TH><TH>Details</TH><TH>Used</TH></TR>\n")

    for function_tuple in functiontuplelist: # list of tuples describing every function file name and line number as an HTML reference
        # HTML[j]ref links to function Code / [ApiDoc]
        HTMLref = os.path.split(function_tuple[2].fileName)[1].replace(".", "_")
        HTMLref += "_" + `function_tuple[2].uniqueNumber` + ".html"
        if function_tuple[1].javadoc.isDefault():
            HTMLjref = ''
        else:
            HTMLjref = HTMLref + '#' + function_tuple[1].javadoc.name + '_' + `function_tuple[1].uniqueNumber`
        # HTMLp[j]ref links to package Code [ApiDoc]
        if function_tuple[3].javadoc.isDefault():
            HTMLpjref = ''
        else:
            HTMLpjref = HTMLref + '#' + function_tuple[3].packageName.lower() + '_' + `function_tuple[3].uniqueNumber`
        HTMLpref = HTMLref + "#" + `function_tuple[3].lineNumber`
        HTMLref += "#" + `function_tuple[1].lineNumber`
        if HTMLjref == '':
            outfile.write("  <TR><TD>" + function_tuple[1].functionName.lower() + " <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        else:
            outfile.write("  <TR><TD><A HREF='" + HTMLjref + "'>" + function_tuple[1].functionName.lower() + "</A> <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        outfile.write("<TD>")
        if HTMLpjref == '':
            outfile.write(function_tuple[3].packageName.lower() + " <SUP><A HREF='" + HTMLpref + "'>#</A>")
        else:
            outfile.write("<A HREF='" + HTMLpjref + "'>" + function_tuple[3].packageName.lower() + "</A> <SUP><A HREF='" + HTMLpref + "'>#</A>")
        outfile.write("</TD>")
        outfile.write("<TD>" + JavaDocShortDesc(function_tuple[1].javadoc.desc) + "</TD>")
        if len(function_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `function_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD><A href=\"" + HTMLwhereusedref + "\">where used list</A></TD>\n")
        else:
            outfile.write("<TD>no use found by HyperSQL</TD>")
        outfile.write("</TR>\n")

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()


def MakeProcedureIndex(meta_info):
    """Generate HTML index page for all procedures"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.procedureIndex_FileName
    top_level_directory = meta_info.topLevelDirectory

    proceduretuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            for procedure_info in package_info.procedureInfoList:
                proceduretuplelist.append((procedure_info.procedureName.upper(), procedure_info, file_info, package_info)) # append as tuple for case insensitive sort

    proceduretuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'Procedure Index'))
    outfile.write("<H1>Index Of All Procedures</H1>\n")
    outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
    outfile.write("  <TR><TH>Procedure</TH><TH>from Package</TH><TH>Details</TH><TH>Used</TH></TR>\n")

    for procedure_tuple in proceduretuplelist: # list of tuples describing every function
        # file name and line number as an HTML reference
        # HTML[j]ref links to procedure Code [ApiDoc]
        HTMLref = os.path.split(procedure_tuple[2].fileName)[1].replace(".", "_")
        HTMLref += "_" + `procedure_tuple[2].uniqueNumber` + ".html"
        if procedure_tuple[1].javadoc.isDefault():
            HTMLjref = ''
        else:
            HTMLjref = HTMLref + '#' + procedure_tuple[1].javadoc.name + '_' + `procedure_tuple[1].uniqueNumber`
        # HTMLp[j]ref links to package Code [ApiDoc]
        if procedure_tuple[3].javadoc.isDefault():
            HTMLpjref = ''
        else:
            HTMLpjref = HTMLref + '#' + procedure_tuple[3].packageName.lower() + '_' + `procedure_tuple[3].uniqueNumber`
        HTMLpref = HTMLref + "#" + `procedure_tuple[3].lineNumber`
        HTMLref += "#" + `procedure_tuple[1].lineNumber`
        if HTMLjref == '':
            outfile.write("  <TR><TD>" + procedure_tuple[1].procedureName.lower() + " <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        else:
            outfile.write("  <TR><TD><A HREF='" + HTMLjref + "'>" + procedure_tuple[1].procedureName.lower() + "</A> <SUP><A href=\"" + HTMLref + "\">#</SUP></A></TD>")
        outfile.write("<TD>")
        if HTMLpjref == '':
            outfile.write(procedure_tuple[3].packageName.lower() + " <SUP><A HREF='" + HTMLpref + "'>#</A>")
        else:
            outfile.write("<A HREF='" + HTMLpjref + "'>" + procedure_tuple[3].packageName.lower() + "</A> <SUP><A HREF='" + HTMLpref + "'>#</A>")
        outfile.write("</TD>")
        outfile.write("<TD>" + JavaDocShortDesc(procedure_tuple[1].javadoc.desc) + "</TD>")
        if len(procedure_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `procedure_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD><A href=\"" + HTMLwhereusedref + "\">where used list</A></TD>")
        else:
            outfile.write("<TD>no use found by HyperSQL</TD>")
        outfile.write("</TR>\n")

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter())
    outfile.close()

def MakePackagesWithFuncsAndProcsIndex(meta_info):
    """Generate HTML index page for all packages, including their functions and procedures"""

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    outfilename = meta_info.packageFuncProdIndex_FileName
    top_level_directory = meta_info.topLevelDirectory

    packagetuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.packageName.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(meta_info, 'Full Package Index'))
    outfile.write("<H1>Index Of All Packages, Their Functions And Procedures</H1>\n")

    for package_tuple in packagetuplelist:
        # file name and line number as an HTML reference
        HTMLref = os.path.split(package_tuple[2].fileName)[1].replace(".", "_")
        HTMLref += "_" + `package_tuple[2].uniqueNumber` + ".html"
        if package_tuple[1].javadoc.isDefault():
            HTMLjref = ''
        else:
            HTMLjref = HTMLref + '#' + package_tuple[1].javadoc.name + `package_tuple[1].uniqueNumber`
        HTMLref += "#" + `package_tuple[1].lineNumber`
        outfile.write("<TABLE CLASS='apilist' ALIGN='center' WIDTH='98%'>\n  <TR><TH COLSPAN='3'>" + package_tuple[1].packageName.lower() + "</TH></TR>\n")
        outfile.write("  <TR><TD ALIGN='center' WIDTH='33.33%'><A href=\"" + HTMLref + "\">Code</A></TD><TD ALIGN='center' WIDTH='33.34%'>")
        if HTMLjref == '':
            outfile.write("&nbsp;")
        else:
            outfile.write("<A HREF='" + HTMLjref + "'>ApiDoc</A>")
        outfile.write("</TD><TD ALIGN='center' WIDTH='33.33%'>")
        if len(package_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write("<A href=\"" + HTMLwhereusedref + "\">Where Used</A>")
        else:
            outfile.write("no use found by HyperSQL")
        outfile.write("</TD></TR>\n")

        # functions in this package
        functiontuplelist = []
        for function_info in package_tuple[1].functionInfoList:
            functiontuplelist.append((function_info.functionName.upper(), function_info, package_tuple[2])) # append as tuple for case insensitive sort

        functiontuplelist.sort(TupleCompareFirstElements)
        if len(functiontuplelist) != 0:
            outfile.write("  <TR><TH class='sub' COLSPAN='3'>Functions</TH></TR>\n  <TR><TD COLSPAN='3'>")
            outfile.write("<TABLE ALIGN='center'>\n")
            outfile.write("    <TR><TD ALIGN='center'><B>Function</B></TD><TD ALIGN='center'><B>Details</B></TD><TD ALIGN='center'><B>Used</B></TD></TR>\n")
        for function_tuple in functiontuplelist:
            HTMLref = os.path.split(function_tuple[2].fileName)[1].replace(".", "_")
            HTMLref += "_" + `function_tuple[2].uniqueNumber` + ".html"
            HTMLref += "#" + `function_tuple[1].lineNumber`
            outfile.write("    <TR><TD><A href=\"" + HTMLref + "\">" + function_tuple[1].functionName.lower() + "</A></TD>\n")
            outfile.write("<TD>" + JavaDocShortDesc(function_tuple[1].javadoc.desc) + "</TD>")
            outfile.write("        <TD>")
            if len(function_tuple[1].whereUsed.keys()) > 0:
                HTMLwhereusedref = "where_used_" + `function_tuple[1].uniqueNumber` + ".html"
                outfile.write("<A href=\"" + HTMLwhereusedref + "\">where used list</A>")
            else:
                outfile.write("no use found by HyperSQL")
            outfile.write("</TD></TR>\n")
        if len(functiontuplelist) != 0:
            outfile.write("</TABLE></TD></TR>\n")
	    
        # procedures in this package
        proceduretuplelist = []
        for procedure_info in package_tuple[1].procedureInfoList:
            proceduretuplelist.append((procedure_info.procedureName.upper(), procedure_info, package_tuple[2])) # append as tuple for case insensitive sort

        proceduretuplelist.sort(TupleCompareFirstElements)
        if len(proceduretuplelist) != 0:
            outfile.write("  <TR><TH class='sub' COLSPAN='3'>Procedures</TH></TR>\n  <TR><TD COLSPAN='3'>")
            outfile.write("<TABLE ALIGN='center'>\n")
            outfile.write("    <TR><TD ALIGN='center'><B>Procedure</B></TD><TD ALIGN='center'><B>Details</B></TD><TD ALIGN='center'><B>Used</B></TD></TR>\n")
        for procedure_tuple in proceduretuplelist:
            HTMLref = os.path.split(procedure_tuple[2].fileName)[1].replace(".", "_")
            HTMLref += "_" + `procedure_tuple[2].uniqueNumber` + ".html"
            HTMLref += "#" + `procedure_tuple[1].lineNumber`
            outfile.write("    <TR><TD><A href=\"" + HTMLref + "\">" + procedure_tuple[1].procedureName.lower() + "</A></TD>\n")
            outfile.write("<TD>" + JavaDocShortDesc(procedure_tuple[1].javadoc.desc) + "</TD>")
            outfile.write("        <TD>")
            if len(procedure_tuple[1].whereUsed.keys()) > 0:
                HTMLwhereusedref = "where_used_" + `procedure_tuple[1].uniqueNumber` + ".html"
                outfile.write("<A href=\"" + HTMLwhereusedref + "\">where used list</A>")
            else:
                outfile.write("no use found by HyperSQL")
            outfile.write("</TD></TR>\n")
        if len(proceduretuplelist) != 0:
            outfile.write("</TABLE></TD></TR>\n")
        outfile.write("</TABLE>\n")

    outfile.write(MakeHTMLFooter())
    outfile.close()


def CreateHyperlinkedSourceFilePages(meta_info):
    """
    Generates pages with the complete source code of each file, including link
    targets (A NAME=) for each line. This way we can link directly to the line
    starting the definition of an object, or where it is called (used) from.
    Very basic syntax highlighting is performed here as well.
    """

    fileInfoList = meta_info.fileInfoList
    html_dir = meta_info.htmlDir
    top_level_directory = meta_info.topLevelDirectory

    sqlkeywords = []
    sqltypes    = []
    for line in fileinput.input(os.path.split(sys.argv[0])[0] + os.sep + 'sql.keywords'):
      if line.strip()[0]=='#':
        continue
      sqlkeywords.append(line.strip())
    for line in fileinput.input(os.path.split(sys.argv[0])[0] + os.sep + 'sql.types'):
      if line.strip()[0]=='#':
        continue
      sqltypes.append(line.strip())

    dot_count = 1
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

	# print a . every file
	sys.stdout.write(".")
	sys.stdout.flush()
	if (dot_count % 60) == 0: # carriage return every 60 dots
	    print
	    sys.stdout.flush()
	dot_count += 1

        # read up the source file
        infile = open(file_info.fileName, "r")
        infile_line_list = infile.readlines()
        infile.close()

        # generate a file name for us to write to (+1 for delimiter)
        outfilename = os.path.split(file_info.fileName)[1].replace(".", "_")
        outfilename += "_" + `file_info.uniqueNumber` + ".html"

        # we need leading zeroes for the line numbers
        line_number_width = len(`len(infile_line_list)`) # number of chars in "number of lines of text"

        outfile = open(html_dir + outfilename, "w")
        outfile.write(MakeHTMLHeader(meta_info, file_info.fileName[len(top_level_directory)+1:]))
        outfile.write("<H1>" + file_info.fileName[len(top_level_directory)+1:] + "</H1>\n")

        # ===[ JAVADOC STARTS HERE ]===
        # Do we have views in this file?
        viewdetails = '\n\n'
        if len(file_info.viewInfoList) > 0:
            print 'We have views here'

        # Do we have packages in this file?
        packagedetails = '\n\n'
        if len(file_info.packageInfoList) > 0:
            outfile.write('<H2 CLASS="api">Package Overview</H2>\n')
            outfile.write('<TABLE CLASS="apilist" ALIGN="center">\n')
            for p in range(len(file_info.packageInfoList)):
                jdoc = file_info.packageInfoList[p].javadoc
                outfile.write(' <TR><TH COLSPAN="2">' + file_info.packageInfoList[p].packageName + '</TH></TR>\n')
                outfile.write(' <TR><TD COLSPAN="2">')
                if jdoc.desc != '':
                  outfile.write('<DIV>' + jdoc.desc + '</DIV>')
                if jdoc.version !='' or jdoc.author != '' or jdoc.info != '' or jdoc.todo != '':
                  outfile.write('<DL>')
                  if jdoc.author != '':
                    outfile.write('<DT>Author:</DT><DD>' + jdoc.author + '</DD>')
                  if jdoc.version != '':
                    outfile.write('<DT>Version:</DT><DD>' + jdoc.version + '</DD>')
                  if jdoc.copyright != '':
                    outfile.write('<DT>Copyright:</DT><DD>' + jdoc.copyright + '</DD>')
                  if jdoc.license != '':
                    outfile.write('<DT>License:</DT><DD>' + jdoc.license + '</DD>')
                  if jdoc.webpage != '':
                    outfile.write('<DT>Webpage:</DT><DD><A HREF="' + jdoc.webpage + '">' + jdoc.webpage + '</A></DD>')
                  if jdoc.see != '':
                    outfile.write('<DT>See also:</DT><DD>' + jdoc.see + '</DD>')
                  if jdoc.info != '':
                    outfile.write('<DT>Additional Information:</DT><DD>' + jdoc.info + '</DD>')
                  if jdoc.todo != '':
                    outfile.write('<DT>TODO:</DT><DD>' + jdoc.todo + '</DD>')
                  if jdoc.bug != '':
                    outfile.write('<DT>BUG:</DT><DD>' + jdoc.bug + '</DD>')
                  if jdoc.deprecated != '':
                    outfile.write('<DT>DEPRECATED:</DT><DD>' + jdoc.deprecated + '</DD>')
                  outfile.write('</DL>')
                outfile.write('</TD></TR>\n')
                # Check the packages for functions
                if len(file_info.packageInfoList[p].functionInfoList) > 0:
                    packagedetails += '<A NAME="funcs"></A><H2>Functions</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="2">Functions</TH></TR>\n')
                    for item in file_info.packageInfoList[p].functionInfoList:
                        if item.javadoc.name != '':
                            iname = '<A HREF="#'+item.javadoc.name+'_'+str(item.uniqueNumber)+'">'+item.javadoc.name+'</A>'
                            idesc = JavaDocShortDesc(item.javadoc.desc)
                        else:
                            iname = item.functionName
                            idesc = ''
                        outfile.write(' <TR><TD><DIV STYLE="margin-left:15px;text-indent:-15px;">'+iname)
                        outfile.write('<SUP><A HREF="#'+str(item.lineNumber)+'">#</A></SUP>')
                        outfile.write(' (')
                        if len(item.javadoc.params) > 0:
                            ph = ''
                            for par in item.javadoc.params:
                                ph += ', '+par.sqltype+' '+par.name
                            outfile.write(ph[2:])
                        outfile.write(')</DIV></TD><TD>'+idesc+'</TD></TR>\n')
                        if item.javadoc.isDefault():
                            continue
                        packagedetails += JavaDocApiElem(item.javadoc,item.uniqueNumber)
                # Check the packages for procedures
                if len(file_info.packageInfoList[p].procedureInfoList) > 0:
                    packagedetails += '<A NAME="procs"></A><H2>Procedures</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="2">Procedures</TH></TR>\n')
                    for item in file_info.packageInfoList[p].procedureInfoList:
                        if item.javadoc.name != '':
                            iname = '<A HREF="#'+item.javadoc.name+'_'+str(item.uniqueNumber)+'">'+item.javadoc.name+'</A>'
                            idesc = JavaDocShortDesc(item.javadoc.desc)
                        else:
                            iname = item.procedureName
                            idesc = ''
                        outfile.write(' <TR><TD><DIV STYLE="margin-left:15px;text-indent:-15px;">'+iname)
                        outfile.write('<SUP><A HREF="#'+str(item.lineNumber)+'">#</A></SUP>')
                        outfile.write(' (')
                        if len(item.javadoc.params) > 0:
                            ph = ''
                            for par in item.javadoc.params:
                                ph += ', '+par.sqltype+' '+par.name
                            outfile.write(ph[2:])
                        outfile.write(')</DIV></TD><TD>'+idesc+'</TD></TR>\n')
                        if item.javadoc.isDefault():
                            continue
                        packagedetails += JavaDocApiElem(item.javadoc,item.uniqueNumber)
            outfile.write('</TABLE>\n\n')

        outfile.write(viewdetails)
        outfile.write(packagedetails)
        # ===[ JAVADOC END ]===

        outfile.write('\n<H2>Source</H2>\n')

        # use non-linw-wrapping monospaced font, text is preformatted in terms of whitespace
        outfile.write('<code><pre><br>')

        for line_number in range(len(infile_line_list)):
            infile_line_list[line_number] = escape(infile_line_list[line_number])
            if infile_line_list[line_number].strip()[0:2]=='--':
              text = '<SPAN CLASS="sqlcomment">' + infile_line_list[line_number] + '</SPAN>'
            else:
              text = infile_line_list[line_number]
              prel = len(text) - len(text.lstrip())
              text = text[0:prel]
              commentmode = 0 # 0 no comment, 1 '--', 2 '/*'
              for elem in infile_line_list[line_number].split():
                if elem[len(elem)-1] in [',', ';', ')', '}', ']'] and len(elem)>1:
                  selem = elem[0:len(elem)-1]
                  echar  = elem[len(elem)-1]
                  if echar in [')', '}', ']']:
                    echar = '<SPAN CLASS="sqlbrace">' + echar + '</SPAN>'
                else:
                  selem = elem
                  echar  = ''
                if selem[0:1] in ['(', '{', '['] and len(selem)>1:
                  schar = '<SPAN CLASS="sqlbrace">' + selem[0:1] + '</SPAN>'
                  selem = selem[1:]
                else:
                  schar = ''
                if commentmode==0:
                  if selem[0:2]=='--':
                    text += schar + '<SPAN CLASS="sqlcomment">' + echar + selem
                    commentmode = 1
                  elif selem in sqlkeywords:
                    text += schar + '<SPAN CLASS="sqlkeyword">' + selem + '</SPAN> ' + echar
                  elif selem in sqltypes:
                    text += schar + '<SPAN CLASS="sqltype">' + selem + '</SPAN> ' + echar
                  elif selem in ['(', ')', '[', ']', '{', '}']:
                    text += '<SPAN CLASS="sqlbrace">' + selem + echar + '</SPAN>'
                  else:
                    text += schar + selem + echar + ' '
                else: # 1 for now
                  text += ' ' + schar + selem + echar
              if commentmode==1:
                text += '</SPAN>'
              text += "\n"
            zeroes = (1 + line_number_width - len(`line_number`)) * "0" # leading zeroes for line numbers
            outfile.write("<A NAME=\"" + `line_number` + "\"></A>") # hyperlink target
            outfile.write(zeroes + `line_number` + ": " + text) #text

        outfile.write("</pre></code><br>")
        outfile.write(MakeHTMLFooter())
        outfile.close()

    # print carriage return after last dot
    print


def CreateIndexPage(meta_info):
    """Generates the main index page"""

    html_dir = meta_info.htmlDir
    script_name = meta_info.scriptName

    outfile = open(html_dir + 'index.html', "w")
    outfile.write(MakeHTMLHeader(meta_info, 'Index'))

    # Copy the StyleSheet
    if os.path.exists(meta_info.css_file):
      copy2(meta_info.css_file,html_dir + os.path.split(meta_info.css_file)[1])

    outfile.write("<H1 STYLE='margin-top:100px'>" + metaInfo.title_prefix + " HyperSQL Reference</H1>\n")

    outfile.write("<BR><BR>\n")
    outfile.write("<TABLE ID='projectinfo' ALIGN='center'><TR><TD VALIGN='middle' ALIGN='center'>\n")
    if meta_info.projectLogo != '':
      logoname = os.path.split(meta_info.projectLogo)[1]
      copy2(meta_info.projectLogo,html_dir + logoname)
      outfile.write("  <IMG ALIGN='center' SRC='" + logoname + "' ALT='Logo'><BR><BR><BR>\n")
    outfile.write(meta_info.projectInfo)
    outfile.write("</TD></TR></TABLE>\n")
    outfile.write("<BR><BR>\n")

    outfile.write(MakeHTMLFooter())
    outfile.close()


def CreateWhereUsedPages(meta_info):
    """Generate a where-used-page for each object"""

    html_dir = meta_info.htmlDir
    fileInfoList = meta_info.fileInfoList

    # loop through files
    dot_count = 1
    for file_info in fileInfoList:

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

	# print a . every file
	sys.stdout.write(".")
	sys.stdout.flush()
	if (dot_count % 60) == 0: # carriage return every 60 dots
	    print
	    sys.stdout.flush()
	dot_count += 1
	
        # loop through views
        for view_info in file_info.viewInfoList:

            if len(view_info.whereUsed.keys()) == 0:
                continue
            
            #open a "where used" file
            whereusedfilename = "where_used_" + `view_info.uniqueNumber` + ".html"
            outfile = open(html_dir + whereusedfilename, "w")
            
            # write our header
            outfile.write(MakeHTMLHeader(meta_info, 'Index'))
            outfile.write("<H1>" + view_info.viewName + " Where Used List</H1>\n")
            outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
            outfile.write("  <TR><TH>File</TH><TH>Line</TH></TR>\n")

            # each where used
            where_used_keys = view_info.whereUsed.keys()
            where_used_keys.sort(CaseInsensitiveComparison)
            for key in where_used_keys:
                for whereusedtuple in view_info.whereUsed[key]:
                    line_number = whereusedtuple[1]
                    unique_number = whereusedtuple[0].uniqueNumber
                    outfile.write("  <TR><TD>")

                    # only make hypertext references for SQL files for now
                    if whereusedtuple[0].fileType == "sql":
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                        outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                        outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                        outfile.write( `line_number` + "</A>")
                    else:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

            # footer and close
            outfile.write("</TABLE>")
            outfile.write(MakeHTMLFooter())
            outfile.close()

        for package_info in file_info.packageInfoList:

            if len(package_info.whereUsed.keys()) == 0:
                continue
            
            #open a "where used" file
            whereusedfilename = "where_used_" + `package_info.uniqueNumber` + ".html"
            outfile = open(html_dir + whereusedfilename, "w")
            
            # write our header
            outfile.write(MakeHTMLHeader(meta_info, package_info.packageName + " Where Used List"))
            outfile.write("<H1>" + package_info.packageName + " Where Used List</H1>\n")
            outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
            outfile.write("  <TR><TH>File</TH><TH>Line</TH></TR>\n")

            # each where used
            where_used_keys = package_info.whereUsed.keys()
            where_used_keys.sort(CaseInsensitiveComparison)
            for key in where_used_keys:
                for whereusedtuple in package_info.whereUsed[key]:
                    line_number = whereusedtuple[1]
                    unique_number = whereusedtuple[0].uniqueNumber
                    outfile.write("  <TR><TD>")

                    # only make hypertext references for SQL files for now
                    if whereusedtuple[0].fileType == "sql":
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                        outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                        outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                        outfile.write(`line_number` + "</A>")
                    else:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

            # footer and close
            outfile.write("</TABLE>")
            outfile.write(MakeHTMLFooter())
            outfile.close()

            #look for any of this packages' functions
            for function_info in package_info.functionInfoList:
                if len(function_info.whereUsed.keys()) == 0:
                    continue
                
                #open a "where used" file
                whereusedfilename = "where_used_" + `function_info.uniqueNumber` + ".html"
                outfile = open(html_dir + whereusedfilename, "w")
                
                # write our header
                outfile.write(MakeHTMLHeader(meta_info, function_info.functionName.lower() + ' from ' + package_info.packageName))
                outfile.write("<H1>" + function_info.functionName.lower() + " <I>from " + package_info.packageName)
                outfile.write(" </I>Where Used List</H1>\n")
                outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
                outfile.write("  <TR><TH>File</TH><TH>Line</TH></TR>\n")

                # each where used
                where_used_keys = function_info.whereUsed.keys()
                where_used_keys.sort(CaseInsensitiveComparison)
                for key in where_used_keys:
                    for whereusedtuple in function_info.whereUsed[key]:
                        line_number = whereusedtuple[1]
                        unique_number = whereusedtuple[0].uniqueNumber

                    # only make hypertext references for SQL files for now
                    outfile.write("  <TR><TD>")
                    if whereusedtuple[0].fileType == "sql":
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                        outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                        outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                        outfile.write(`line_number` + "</A>")
                    else:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

                # footer and close
                outfile.write("</TABLE>")
                outfile.write(MakeHTMLFooter())
                outfile.close()

            #look for any of this packages procedures
            for procedure_info in package_info.procedureInfoList:
                if len(procedure_info.whereUsed.keys()) == 0:
                    continue
                
                #open a "where used" file
                whereusedfilename = "where_used_" + `procedure_info.uniqueNumber` + ".html"
                outfile = open(html_dir + whereusedfilename, "w")
                
                # write our header
                outfile.write(MakeHTMLHeader(meta_info, procedure_info.procedureName.lower() + ' from ' + package_info.packageName.lower()))
                outfile.write("<H1>" + procedure_info.procedureName.lower() + " <I>from " + package_info.packageName.lower())
                outfile.write(" </I>Where Used List</H1>\n")
                outfile.write("<TABLE CLASS='apilist' ALIGN='center'>\n")
                outfile.write("  <TR><TH>File</TH><TH>Line</TH></TR>\n")
                
                # each where used
                where_used_keys = procedure_info.whereUsed.keys()
                where_used_keys.sort(CaseInsensitiveComparison)
                for key in where_used_keys:
                    for whereusedtuple in procedure_info.whereUsed[key]:
                        line_number = whereusedtuple[1]
                        unique_number = whereusedtuple[0].uniqueNumber
                        outfile.write("  <TR><TD>")

                        # only make hypertext references for SQL files for now
                        if whereusedtuple[0].fileType == "sql":
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                            outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                            outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                            outfile.write(`line_number` + "</A>")
                        else:
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

                # footer and close
                outfile.write("</TABLE>")
                outfile.write(MakeHTMLFooter())
                outfile.close()

    # print carriage return after last dot
    print


def confName(projName):
    """ Get the name of the .ini file to use for configuration """
    if os.path.exists(projName+'.ini'):
      return projName+'.ini'
    if os.path.exists(projName.lower()+'.ini'):
      return projName.lower()+'.ini'
    if os.path.exists('HyperSQL.ini'):
      return 'HyperSQL.ini'
    if os.path.exists('hypersql.ini'):
      return 'hypersql.ini'
    return ''

def confGet(sect,opt,default=''):
    """
    Get an option from the config as string
    Parameters: section name, option name, default value
    """
    if config.has_option(sect,opt):
      return config.get(sect,opt)
    else:
      return default

def confGetList(sect,opt,default=[]):
    """
    Get an option from the config as list
    Parameters: section name, option name, default value
    """
    if config.has_option(sect,opt):
      return config.get(sect,opt).split(' ')
    else:
      return default

def confGetBool(sect,opt,default=False):
    """
    Get an option from the config as boolean value
    Parameters: section name, option name, default value
    """
    if config.has_option(sect,opt):
      return config.getboolean(sect,opt)
    else:
      return default

if __name__ == "__main__":

    # Read the config file
    if len(sys.argv)>1:
      configFile = confName(sys.argv[1])
    else:
      configFile = confName('HyperSQL')
    config = ConfigParser.ConfigParser()
    if configFile != '':
      print 'Reading config file ' + configFile
      config.read(configFile)

    top_level_directory = confGet('General','top_level_directory','.') # directory under which all files will be scanned
    metaInfo = MetaInfo() # This holds top-level meta information, i.e., lists of filenames, etc.
    metaInfo.title_prefix  = confGet('General','title_prefix','HyperSQL')
    metaInfo.sql_file_exts = confGetList('General','sql_file_exts',['sql', 'pkg', 'pkb', 'pks', 'pls']) # Extensions for files to treat as SQL
    metaInfo.cpp_file_exts = confGetList('General','cpp_file_exts',['c', 'cpp', 'h']) # Extensions for files to treat as C
    metaInfo.css_file      = confGet('General','css_file','hypersql.css')
    metaInfo.rcsnames      = confGetList('FileNames','rcsnames',['RCS','CVS','.svn']) # directories to ignore
    metaInfo.fileWithPathnamesIndex_FileName = confGet('FileNames','FileWithPathnamesIndex','FileNameIndexWithPathnames.html')
    metaInfo.fileNoPathnamesIndex_FileName   = confGet('FileNames','FileNoPathnamesIndex','FileNameIndexNoPathnames.html')
    metaInfo.viewIndex_FileName              = confGet('FileNames','viewIndex','ViewIndex.html')
    metaInfo.packageIndex_FileName           = confGet('FileNames','packageIndex','PackageIndex.html')
    metaInfo.functionIndex_FileName          = confGet('FileNames','functionIndex','FunctionIndex.html')
    metaInfo.procedureIndex_FileName         = confGet('FileNames','procedureIndex','ProcedureIndex.html')
    metaInfo.packageFuncProdIndex_FileName   = confGet('FileNames','packageFuncProdIndex','PackagesWithFuncsAndProcsIndex.html')
    metaInfo.htmlDir = confGet('FileNames','htmlDir',os.path.split(sys.argv[0])[0] + os.sep + "html" + os.sep)
    metaInfo.projectLogo = confGet('General','project_logo','')
    metaInfo.projectInfo = confGet('General','project_info','This is my HyperSQL project.')
    purgeOnStart = confGetBool('General','purge_on_start',False)

    metaInfo.topLevelDirectory = top_level_directory
    metaInfo.scriptName = sys.argv[0]
    metaInfo.versionString = "1.6" 
    metaInfo.toDoList = """
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #   TO-DO LIST
    #
    # A) where used does not work for local functions or procedures
    # B) block comments are not ignored (/* comment block */)
    # C) C++ files need doxygen hyperlinks for where used pages
    # D) Scan Java files for where used
    #
    # If you have an idea for improving hyperSQL, let me know - Randy
    #
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    """



    print "Creating file list" 
    FindFilesAndBuildFileList(metaInfo.topLevelDirectory, metaInfo.fileInfoList, metaInfo)

    print "Scanning source files for views and packages"
    ScanFilesForViewsAndPackages(metaInfo)

    print "Scanning source files for where views and packages are used"
    ScanFilesForWhereViewsAndPackagesAreUsed(metaInfo)

    if purgeOnStart and os.path.exists(metaInfo.htmlDir):
      print "Removing html files from previous run"
      names=os.listdir(metaInfo.htmlDir)
      for i in names:
        os.unlink(metaInfo.htmlDir + i)

    print "Creating html subdirectory"
    CreateHTMLDirectory(metaInfo)

    print "Creating filename by path index"
    MakeFileIndexWithPathNames(metaInfo)

    print "Creating filename no path index"
    MakeFileIndexNoPathNames(metaInfo)

    print "Creating view index"
    MakeViewIndex(metaInfo)

    print "Creating package index"
    MakePackageIndex(metaInfo)

    print "Creating function index"
    MakeFunctionIndex(metaInfo)

    print "Creating procedure index"
    MakeProcedureIndex(metaInfo)

    print "Creating 'package with functions and procedures' index"
    MakePackagesWithFuncsAndProcsIndex(metaInfo)

    print "Creating 'where used' pages"
    CreateWhereUsedPages(metaInfo)

    print "Creating hyperlinked source file pages"
    CreateHyperlinkedSourceFilePages(metaInfo)

    print "Creating site index page"
    CreateIndexPage(metaInfo)

    print metaInfo.toDoList

    print "done"
