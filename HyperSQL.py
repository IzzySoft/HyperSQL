#!/usr/bin/python

# see main function at bottom of file

"""
    $Id$
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

    Author contact information:
       randy-san@users.sourceforge.net
       izzysoft AT qumran DOT org
"""

# first import standard modules we use
import os, sys, string, time, ConfigParser, fileinput, logging, re, gettext, locale
from shutil import copy2

# now import our own modules
sys.path.insert(0,os.path.split(sys.argv[0])[0] + os.sep + 'lib')
from hypercore import *
from hyperjdoc import *
from hypercode import *
from hyperconf import *
from hypercharts import *

def FindFilesAndBuildFileList(dir, fileInfoList, init=True):
    """
    Recursively scans the source directory specified for relevant files according
    to the file extensions configured in metaInfo, while excluding RCS
    directories (see rcsnames in configuration section FileNames). Information
    for matching files is stored in fileInfoList.
    @param string dir directory to scan
    @param list fileInfoList where to store results
    """
    if init: # do not print this on recursive calls
        printProgress(_("Creating file list"))

    # get a list of this directory's contents
    # these items are relative and not absolute
    names=os.listdir(dir)

    # iterate through the file list
    for i in names: 

      if i in metaInfo.rcsnames: # do not look in RCS/CVS/SVN/... special dirs
	    continue

      # convert from relative to absolute addressing
      # to allow recursive calls
      f1=os.path.join(dir, i)

      # if this item is also a directory, recurse it too
      if os.path.isdir(f1):
        FindFilesAndBuildFileList(f1, fileInfoList, False)
	    
      else:  # file found, only add specific file extensions to the list
        fspl = f1.split('.')
        ext  = fspl[len(fspl)-1]
        if ext in metaInfo.sql_file_exts:
          temp = FileInfo()
          temp.fileName = f1
          temp.fileType = "sql"
          if temp.uniqueNumber == 0:
            temp.uniqueNumber = metaInfo.NextIndex()
          fileInfoList.append(temp)
        if ext in metaInfo.cpp_file_exts:
          temp = FileInfo()
          temp.fileName = f1
          temp.fileType = "cpp"
          if temp.uniqueNumber == 0:
            temp.uniqueNumber = metaInfo.NextIndex()
          fileInfoList.append(temp)

def ScanFilesForViewsAndPackages():
    """
    Scans files from metaInfo.fileInfoList for views and packages and collects
    some metadata about them (name, file, lineno). When encountering a package
    spec, it also scans for its functions and procedures.
    It simply searches the source file for keywords. With each object info,
    file name and line number are stored (and can be used to identify parent
    and children) - for functions and procedures contained in packages, a link
    to their parent is stored along.
    """
    printProgress(_("Scanning source files for views and packages"))

    fileInfoList = metaInfo.fileInfoList
    strpatt = re.compile("('[^']*')+")    # String-Regexp

    # first, find views in files
    dot_count = 1
    for file_info in fileInfoList:

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue
        
        # print a . every file
        dotProgress(dot_count)

        dot_count += 1
        infile = open(file_info.fileName, "r")
        fileLines = infile.readlines()
        infile.close()
        file_info.lines = len(fileLines)
        file_info.bytes  = os.path.getsize(file_info.fileName)

        # scan this file for possible JavaDoc style comments
        jdoc = ScanJavaDoc(fileLines, file_info.fileName)

        # if we find a package definition, this flag tells us to also look for
        # functions and procedures.  If we don't find a package definition, there
        # is no reason to look for them
        package_count = -1
        in_block_comment = 0
        new_file = 1

        metaInfo.incLoc('totals',len(fileLines))
        filetext = '\n'.join(fileLines) # complete file in one string
        for lineNumber in range(file_info.lines):
            if len(fileLines[lineNumber].strip()) < 0:
                metaInfo.incLoc('empty')
                continue
            if new_file == 1:
                token_list = fileLines[lineNumber].split()
            else:
                token_list = token_list1

            new_file = 0
            # len()-1 because we start with index 0
            if len(fileLines)-1 > lineNumber:
                # eat string contents
                result = strpatt.search(fileLines[lineNumber+1])
                matched_string = False
                while result != None:
                    matched_string = True
                    for g in range(len(result.groups())):
                        fileLines[lineNumber+1] = fileLines[lineNumber+1].replace(result.group(g) , "")
                    result = strpatt.search(fileLines[lineNumber+1])
                
                token_list1 = fileLines[lineNumber+1].split()
                if matched_string and len(token_list1) < 1: # that line was completely eaten
                    metaInfo.incLoc('code')
                    metaInfo.incLoc('empty',-1)
            else:
                token_list1 = []

            if in_block_comment == 0 and fileLines[lineNumber].strip() != '' \
              and fileLines[lineNumber].find('--') == -1 and fileLines[lineNumber].find('//') == -1 \
              and fileLines[lineNumber].find('##') == -1 and fileLines[lineNumber].find('/*') == -1:
                metaInfo.incLoc('code')

            # ignore lines that begin with comments
            if len(token_list) > 0 and len(token_list[0]) > 1:
                if token_list[0][:2] == "--" or token_list[0][:2] == "//" or token_list[0][:2] == "##":
                    metaInfo.incLoc('comment')
                    continue

            # ignore very short lines
            if len(token_list)<2:
                if len(token_list) > 0:
                    if token_list[0][:2] != "/*" and token_list[0][:2] != "*/":
                        continue
                else:
                    metaInfo.incLoc('empty')
                    continue

            # ignore block comments
            if token_list[0][:2] == "/*" and token_list[0][len(token_list[0])-2:len(token_list[0])] == "*/":
                # block comments like  "/***....*****/": re."/(\*)+/"
                token_list.pop(0)
            elif token_list[0][:2] == "/*" or in_block_comment == 1:
                # 
                in_block_comment = 1
                clean_list = []
                for token_index in range(len(token_list)):
                    if token_list[token_index][:2] == "*/":
                        clean_list.append(token_index)
                        in_block_comment = 0
                    else:
                        clean_list.append(token_index)
                if len(clean_list) > 0:
                    if len(clean_list) == 1:
                        # pop only index 0
                        token_list.pop(clean_list[0])
                    else:
                        for clean_index in range(len(clean_list)-1,-1,-1):
                            # work reverse from back
                            token_list.pop(clean_list[clean_index])
            if  len(token_list) == 0:
                # nothing more on line
                metaInfo.incLoc('comment') # we had just comments in this line (???)
                continue

            # find views.  Loop through looking for the different styles of view definition
            if metaInfo.indexPage['view'] != '':
                for token_index in range(len(token_list)):
                    # look for CREATE VIEW, REPLACE VIEW, FORCE VIEW, making sure enough tokens exist
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "VIEW" \
                    and (token_list[token_index].upper() == "CREATE" \
                        or token_list[token_index].upper() == "REPLACE" \
                        or token_list[token_index].upper() == "FORCE"):
                        view_info = ElemInfo()
                        view_info.parent = file_info
                        if len(token_list) > token_index+2:       
                          view_info.viewName = token_list[token_index+2]
                        else:
                          view_info.view_name = token_list1[0]
                        view_info.lineNumber = lineNumber
                        for j in range(len(jdoc)):
                          ln = jdoc[j].lineNumber - lineNumber
                          if (CaseInsensitiveComparison(view_info.name,jdoc[j].name)==0 and jdoc[j].objectType=='view') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                            view_info.javadoc = jdoc[j]
                        mname = view_info.javadoc.name or package_info.name
                        mands = view_info.javadoc.verify_mandatory()
                        #for mand in mands: Need to setup report here as well! ###TODO###
                        if JavaDocVars['javadoc_mandatory'] and view_info.javadoc.isDefault():
                            logger.warn(_('View %s has no JavaDoc information attached'), view_info.name)
                            #view_info.verification.addItem(view_info.name,'No JavaDoc information available')
                        file_info.viewInfoList.append(view_info)

            # find package definitions - set flag if found
            # look for CREATE [OR REPLACE] PACKAGE BODY x, making sure enough tokens exist
            for token_index in range(len(token_list)):
                if len(token_list) > token_index+3 \
                   and (token_list[token_index].upper() == "CREATE" \
                        or token_list[token_index].upper() == "REPLACE" \
                        or token_list[token_index].upper() == "FORCE") \
                       and token_list[token_index+1].upper() == "PACKAGE" \
                       and token_list[token_index+2].upper() == "BODY":
                    package_info = PackageInfo()
                    package_info.parent = file_info
                    package_info.name = token_list[token_index+3]
                    package_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(package_info.name,jdoc[j].name)==0 and jdoc[j].objectType=='pkg') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                        package_info.javadoc = jdoc[j]
                        if len(jdoc[j].bug) > 0 and metaInfo.indexPage['bug'] != '':
                            for ib in range(len(jdoc[j].bug)):
                                package_info.bugs.addItem(jdoc[j].name,jdoc[j].bug[ib])
                        if len(jdoc[j].todo) > 0 and metaInfo.indexPage['todo'] != '':
                            for ib in range(len(jdoc[j].todo)):
                                package_info.todo.addItem(jdoc[j].name,jdoc[j].todo[ib])
                    mname = package_info.javadoc.name or package_info.name
                    mands = package_info.javadoc.verify_mandatory()
                    for mand in mands:
                        package_info.verification.addItem(mname,mand)
                    if JavaDocVars['javadoc_mandatory'] and package_info.javadoc.isDefault():
                        logger.warn(_('Package %s has no JavaDoc information attached'), mname)
                        package_info.verification.addItem(mname,'No JavaDoc information available')
                    file_info.packageInfoList.append(package_info) # permanent storage
                    package_count += 1 # use this flag below

            # if a package definition was found, look for functions and procedures
            if package_count != -1:
                # first find functions
                if len(token_list) > 1 and token_list[0].upper() == "FUNCTION":
                    function_name = token_list[1].split('(')[0] # some are "name(" and some are "name ("
                    function_info = ElemInfo()
                    function_info.parent = file_info.packageInfoList[package_count]
                    function_info.name = function_name
                    function_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(function_name,jdoc[j].name)==0 and jdoc[j].objectType=='function') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                        if function_info.javadoc.isDefault():
                          function_info.javadoc = jdoc[j]
                          function_info.javadoc.lndiff = abs(ln)
                        else:
                          if abs(ln) < function_info.javadoc.lndiff: # this desc is closer to the object
                            function_info.javadoc = jdoc[j]
                            function_info.javadoc.lndiff = abs(ln)
                        if len(jdoc[j].bug) > 0 and metaInfo.indexPage['bug'] != '':
                            for ib in range(len(jdoc[j].bug)):
                                file_info.packageInfoList[package_count].bugs.addFunc(jdoc[j].name,jdoc[j].bug[ib])
                        if len(jdoc[j].todo) > 0 and metaInfo.indexPage['todo'] != '':
                            for ib in range(len(jdoc[j].todo)):
                                file_info.packageInfoList[package_count].todo.addFunc(jdoc[j].name,jdoc[j].todo[ib])
                    mname = function_info.javadoc.name or function_info.name
                    mands = function_info.javadoc.verify_mandatory()
                    for mand in mands:
                        file_info.packageInfoList[package_count].verification.addFunc(mname,mand)
                    if JavaDocVars['javadoc_mandatory'] and function_info.javadoc.isDefault():
                        logger.warn(_('Function %(function)s in package %(package)s has no JavaDoc information attached'), {'function': mname, 'package': file_info.packageInfoList[package_count].name})
                        file_info.packageInfoList[package_count].verification.addFunc(mname,_('No JavaDoc information available'))
                    if JavaDocVars['verification']:
                        fupatt = re.compile('(?ims)function\s+'+mname+'\s*\((.*?)\)')
                        cparms = re.findall(fupatt,filetext)
                        if len(cparms)==0:
                            mands = function_info.javadoc.verify_params([])
                        elif len(cparms)==1:
                            cparms = cparms[0].split(',')
                            mands = function_info.javadoc.verify_params(cparms)
                        else:
                            logger.debug(_('Multiple definitions for function %(package)s.%(function)s, parameters not verified'), {'package': file_info.packageInfoList[package_count].name, 'function': mname})
                        if len(cparms)<2:
                            for mand in mands:
                                file_info.packageInfoList[package_count].verification.addFunc(mname,mand)
                    file_info.packageInfoList[package_count].functionInfoList.append(function_info)
		    
                # now find procedures
                if len(token_list) > 1 and token_list[0] == "PROCEDURE":
                    procedure_name = token_list[1].split('(')[0] # some are "name(" and some are "name ("
                    procedure_info = ElemInfo()
                    procedure_info.parent = file_info.packageInfoList[package_count]
                    procedure_info.name = procedure_name
                    procedure_info.lineNumber = lineNumber
                    for j in range(len(jdoc)):
                      ln = jdoc[j].lineNumber - lineNumber
                      if (CaseInsensitiveComparison(procedure_name,jdoc[j].name)==0 and jdoc[j].objectType=='procedure') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                        if procedure_info.javadoc.isDefault():
                          procedure_info.javadoc = jdoc[j]
                          procedure_info.javadoc.lndiff = abs(ln)
                        else:
                          if abs(ln) < procedure_info.javadoc.lndiff: # this desc is closer to the object
                            procedure_info.javadoc = jdoc[j]
                            procedure_info.javadoc.lndiff = abs(ln)
                        if len(jdoc[j].bug) > 0 and metaInfo.indexPage['bug'] != '':
                            for ib in range(len(jdoc[j].bug)):
                                file_info.packageInfoList[package_count].bugs.addProc(jdoc[j].name,jdoc[j].bug[ib])
                        if len(jdoc[j].todo) > 0 and metaInfo.indexPage['todo'] != '':
                            for ib in range(len(jdoc[j].todo)):
                                file_info.packageInfoList[package_count].todo.addProc(jdoc[j].name,jdoc[j].todo[ib])
                    mname = procedure_info.javadoc.name or procedure_info.name
                    mands = procedure_info.javadoc.verify_mandatory()
                    for mand in mands:
                        file_info.packageInfoList[package_count].verification.addProc(mname,mand)
                    if JavaDocVars['javadoc_mandatory'] and procedure_info.javadoc.isDefault():
                        logger.warn(_('Procedure %(procedure)s in package %(package)s has no JavaDoc information attached'), {'procedure': mname, 'package': file_info.packageInfoList[package_count].name})
                        file_info.packageInfoList[package_count].verification.addProc(mname,_('No JavaDoc information available'))
                    if JavaDocVars['verification']:
                        fupatt = re.compile('(?ims)procedure\s+'+mname+'\s*\((.*?)\)')
                        cparms = re.findall(fupatt,filetext)
                        if len(cparms)==0:
                            mands = procedure_info.javadoc.verify_params([])
                        elif len(cparms)==1:
                            cparms = cparms[0].split(',')
                            mands = procedure_info.javadoc.verify_params(cparms)
                        else:
                            logger.debug(_('Multiple definitions for function %(package)s.%(function)s, parameters not verified'), {'function': mname, 'package': file_info.packageInfoList[package_count].name})
                        if len(cparms)<2:
                            for mand in mands:
                                file_info.packageInfoList[package_count].verification.addProc(mname,mand)
                    file_info.packageInfoList[package_count].procedureInfoList.append(procedure_info)

    # print carriage return after last dot
    dotFlush()


def ScanFilesForWhereViewsAndPackagesAreUsed():
    """
    Scans files collected in metaInfo.fileInfoList and checks them line by line
    with metaInfo.<object>list for calls to those objects. If it finds any, it
    updates <object>list where_used property accordingly.
    """

    def addWhereUsed(objectInfo,fileInfo,lineNumber):
        """
        Add where_used info to an object (view, procedure, function, ...)
        @param object objectInfo the view_info/function_info/... object used there
        @param object fileInfo object of the file where the usage was found
        @param int lineNumber file line number where the usage was found
        """
        if fileInfo.fileName not in objectInfo.whereUsed.keys():
            objectInfo.whereUsed[fileInfo.fileName] = []
            objectInfo.whereUsed[fileInfo.fileName].append((fileInfo, lineNumber))
        else:
            objectInfo.whereUsed[fileInfo.fileName].append((fileInfo, lineNumber))
        # generate a unique number for use in making where used file if needed
        if objectInfo.uniqueNumber == 0:
            objectInfo.uniqueNumber = metaInfo.NextIndex()


    printProgress(_("Scanning source files for where views and packages are used"))
    scan_instring = config.getBool('Process','whereused_scan_instring')
    if scan_instring:
        logger.info(_('Including strings in where_used scan'))
    else:
        logger.info(_('Excluding strings from where_used scan'))
        strpatt = re.compile("('[^']*')+")    # String-Regexp

    fileInfoList = metaInfo.fileInfoList

    outerfileInfoList = []
    for file_info in fileInfoList:
        outerfileInfoList.append(file_info)

    dot_count = 1
    for outer_file_info in outerfileInfoList:
        # print a . every file
        dotProgress(dot_count)
        dot_count += 1

        infile = open(outer_file_info.fileName, "r")
        fileLines = infile.readlines()
        infile.close()

        # if we find a package definition, this flag tells us to also look for
        # functions and procedures.  If we don't find a package definition, there
        # is no reason to look for them
        package_count = -1
        in_block_comment = 0
        new_file = 1
        

        for lineNumber in range(len(fileLines)):

            if new_file == 1:
                token_list = fileLines[lineNumber].split()
            else:
                token_list = token_list1
                
            # len()-1 because we start with index 0
            if len(fileLines)-1 > lineNumber and not scan_instring:
                # eat string contents
                result = strpatt.search(fileLines[lineNumber+1])
                while result != None:
                    for g in range(len(result.groups())):
                        fileLines[lineNumber+1] = fileLines[lineNumber+1].replace(result.group(g) , "")
                    result = strpatt.search(fileLines[lineNumber+1])

                token_list1 = fileLines[lineNumber+1].split()
            else:
                token_list1 = []
            new_file = 0

            # Skip empty lines
            if len(token_list) < 1:
                continue

            # ignore lines that begin with comments
            if token_list[0][:2] == "--" or token_list[0][:2] == "//" or token_list[0][:2] == "##":
                continue
            # ignore block comments
            if token_list[0][:2] == "/*" and token_list[0][len(token_list[0])-2:len(token_list[0])] == "*/":
                # block comments like  "/***....*****/"
                token_list.pop(0)
            elif token_list[0][:2] == "/*" or in_block_comment == 1:
                # 
                in_block_comment = 1
                clean_list = []
                for token_index in range(len(token_list)):
                    if token_list[token_index][:2] == "*/":
                        clean_list.append(token_index)
                        in_block_comment = 0
                    else:
                        clean_list.append(token_index)
                if len(clean_list) > 0:
                    if len(clean_list) == 1:
                        # pop only index 0
                        token_list.pop(clean_list[0])
                    else:
                        for clean_index in range(len(clean_list)-1,-1,-1):
                            # work reverse from back
                            token_list.pop(clean_list[clean_index])
            if  len(token_list) == 0:
                # nothing more on line
                continue

            # usage only, no creates, replace, force views packages functions or procedures
            usage_flag = 1
            for token_index in range(len(token_list)):

                # look for CREATE VIEW, REPLACE VIEW, FORCE VIEW, making sure enough tokens exist
                if metaInfo.indexPage['view'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "VIEW" \
                and (token_list[token_index].upper() == "CREATE" \
                    or token_list[token_index].upper() == "REPLACE" \
                    or token_list[token_index].upper() == "FORCE"):
                    # we are creating, forcing, or replacing - not using.  Set flag to 0
                    usage_flag = 0

                # look for PACKAGE BODY x IS, making sure enough tokens exist
                if token_list[token_index].upper() == "PACKAGE" \
                and len(token_list) > token_index+2:
                    #and token_list[token_index+1].upper() == "BODY": # commented out - creates trouble if package spec is in the same file
                    package_count += 1 # set flag
                    usage_flag = 0

                # if a package definition was found, look for functions and procedures
                if package_count != -1:
                    # first find functions
                    if token_list[0].upper() == "FUNCTION" and len(token_list) > 1:
                        usage_flag = 0
                    # now find procedures
                    if token_list[0].upper() == "PROCEDURE" and len(token_list) > 1:
                        usage_flag = 0

                # look for END x, making sure enough tokens exist
                if token_list[token_index].upper() == "END" \
                and len(token_list) > token_index+1:
                    usage_flag = 0


            if usage_flag == 0:
                continue

            # Loop through all previously found views and packages to see if they are used in this line of text
            for inner_file_info in fileInfoList:

                # if this FileInfo instance has views
                if len(inner_file_info.viewInfoList) != 0:
                    for view_info in inner_file_info.viewInfoList:
                        # perform case insensitive find
                        if fileLines[lineNumber].upper().find(view_info.name.upper()) != -1:
                            addWhereUsed(view_info, outer_file_info, lineNumber)


                # if this FileInfo instance has packages
                if len(inner_file_info.packageInfoList) != 0:
                    for package_info in inner_file_info.packageInfoList:

                        # perform case insensitive find, this is "package name"."function or procedure name"
                        if fileLines[lineNumber].upper().find(package_info.name.upper() + ".") != -1:

                            addWhereUsed(package_info, outer_file_info, lineNumber)

                            #look for any of this packages' functions
                            for function_info in package_info.functionInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(package_info.name.upper() + "." \
                                  + function_info.name.upper()) != -1:
                                    addWhereUsed(function_info, outer_file_info, lineNumber)

                            #look for any of this packages procedures
                            for procedure_info in package_info.procedureInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(package_info.name.upper() + "." \
                                  + procedure_info.name.upper()) != -1:
                                    addWhereUsed(procedure_info, outer_file_info, lineNumber)

                        ### File internal references - possible calls without a package_name
                        elif (outer_file_info.uniqueNumber == inner_file_info.uniqueNumber) \
                         and config.getBool('Process','whereused_scan_shortrefs'):

                            # check for inline comments to be excluded
                            if fileLines[lineNumber].find('--') == -1:
                              epos = sys.maxint
                            else:
                              epos = fileLines[lineNumber].find('--')

                            #look for any of this packages' functions
                            for function_info in package_info.functionInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(function_info.name.upper()) != -1 \
                                 and (fileLines[lineNumber].upper().find(" " + function_info.name.upper(),0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(function_info.name.upper(),0,epos) == 0) \
                                 and (fileLines[lineNumber].upper().find(function_info.name.upper()+" ",0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(function_info.name.upper()+"(",0,epos) != -1):
                                    addWhereUsed(function_info, outer_file_info, lineNumber)

                            #look for any of this packages procedures
                            for procedure_info in package_info.procedureInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(procedure_info.name.upper(),0,epos) != -1 \
                                 and (fileLines[lineNumber].upper().find(" " + procedure_info.name.upper(),0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(procedure_info.name.upper(),0,epos) == 0) \
                                 and (fileLines[lineNumber].upper().find(procedure_info.name.upper()+" ",0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(procedure_info.name.upper()+"(",0,epos) != -1):
                                    addWhereUsed(procedure_info, outer_file_info, lineNumber)


    # print carriage return after last dot
    dotFlush()


def MakeNavBar(current_page):
    """
    Generates HTML code for the general navigation links to all the index pages
    The current page will be handled separately (no link, highlight)
    @param string current_page name of the current page
    """
    itemCount = 0
    s = "<TABLE CLASS='topbar' WIDTH='98%'><TR>\n"
    s += "  <TD CLASS='navbar' WIDTH='600px'>\n"
    for item in ['package','function','procedure','package_full','view','file','filepath','bug','todo','report','stat']:
        if metaInfo.indexPage[item] == '':
            continue
        if current_page == item:
            s += '    <B><I>' + metaInfo.indexPageName[item] + '</I></B> &nbsp;&nbsp; \n'
        else:
            s += '    <A href="' + metaInfo.indexPage[item] + '">' + metaInfo.indexPageName[item] + '</A> &nbsp;&nbsp; \n'
        itemCount += 1
        if itemCount %4 == 0:
            s += '    <BR>\n'
    if current_page == 'Index':
        s += '    <B><I>'+_('Main Index')+'</I></B>\n'
    else:
        s += '    <A href="index.html">'+_('Main Index')+'</A>\n'
    s += "  </TD><TD CLASS='title'>\n"
    s += '    ' + metaInfo.title_prefix + '\n'
    s += '  </TD>\n'
    s += '</TR></TABLE>\n'
    return s

def MakeHTMLHeader(title_name, charts=False, onload=''):
    """
    Generates common HTML header with menu for all pages
    @param string title_name index key for the title of the current page
    @param optional boolean charts do we need the charts JavaScript? Default: False
    @param optional string onload event for body.onload
    """

    if title_name in metaInfo.indexPageName:
        title_text = metaInfo.indexPageName[title_name]
    else:
        title_text = title_name

    s  = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
    s += '<html><head>\n'
    s += '  <TITLE>' + metaInfo.title_prefix + ': ' + title_text + '</TITLE>\n'
    s += '  <LINK REL="stylesheet" TYPE="text/css" HREF="' + metaInfo.css_file + '">\n'
    s += '  <META HTTP-EQUIV="Content-Type" CONTENT="text/html;charset='+metaInfo.encoding+'">\n'
    if charts:
        s += '  <SCRIPT Language="JavaScript" src="diagram.js" TYPE="text/javascript"></SCRIPT>\n'
    if onload=='':
        s += '</head><body>\n'
    else:
        s += '</head><body onload="'+onload+'">\n'
    s += '<A NAME="topOfPage"></A>\n'
    s += MakeNavBar(title_name)
    s += '<HR CLASS="topend">\n'
    return s

def MakeHTMLFooter(title_name):
    """
    Generates common HTML footer for all pages
    @param string title_name index key for the title of the current page
    """

    if title_name in metaInfo.indexPageName:
        title_text = metaInfo.indexPageName[title_name]
    else:
        title_text = title_name

    s = "<HR CLASS='bottomstart'>\n"
    s += "<DIV ID='bottombar'>\n"
    s += MakeNavBar(title_name)
    s += "  <DIV ID='generated'>Generated by <A HREF='http://projects.izzysoft.de/trac/hypersql/'>HyperSQL</A> v" + metaInfo.versionString + " at " + time.asctime(time.localtime(time.time())) + "</DIV>";
    s += "</DIV>\n"
    s += "</body></html>"
    return s


def CreateHTMLDirectory():
    """Creates the html (output) directory if needed"""
    printProgress(_("Creating html subdirectory"))
    splitted = metaInfo.htmlDir.split(os.sep)
    temp = ""
    for path_element in splitted: # loop through path components, making directories as needed
        temp += path_element + os.sep
        if os.access(temp, os.F_OK) == 1:
            continue
        else:
            os.mkdir(temp)


def getDualCodeLink(otuple):
    """
    Calculates links to Code and JavaDoc ref and returns them as triple HTMLref,HTMLjref,HTMLpref,HTMLpjref
    @return string HTMLref link to code
    @return string HTMLjref link to JavaDoc reference
    @return string HTMLpjref link to JavaDoc package reference
    """
    # HTML[j]ref links to function Code / [ApiDoc]
    HTMLref = os.path.split(otuple[2].fileName)[1].replace(".", "_")
    HTMLref += "_" + `otuple[2].uniqueNumber` + ".html"
    if otuple[1].javadoc.isDefault():
        HTMLjref = ''
    else:
        HTMLjref = HTMLref + '#' + otuple[1].javadoc.name + '_' + `otuple[1].uniqueNumber`
    # HTMLp[j]ref links to package Code [ApiDoc]
    if len(otuple) > 3: # otuple[3] is package_info
        if otuple[3].javadoc.isDefault():
            HTMLpjref = ''
        else:
            HTMLpjref = HTMLref + '#' + otuple[3].name.lower() + '_' + `otuple[3].uniqueNumber`
        HTMLpref = HTMLref + "#" + `otuple[3].lineNumber`
    else:
        HTMLpjref = ''
        HTMLpref  = ''
    HTMLref += "#" + `otuple[1].lineNumber`
    return HTMLref,HTMLjref,HTMLpref,HTMLpjref


def MakeStatsPage():
    """
    Generate Statistics Page
    """

    if metaInfo.indexPage['stat'] == '': # statistics disabled
        return

    printProgress(_('Creating statistics page'))

    outfile = open(metaInfo.htmlDir + metaInfo.indexPage['stat'], 'w')
    outfile.write(MakeHTMLHeader('stat',True,'initCharts();'))
    copy2(scriptpath + os.sep + 'diagram.js', metaInfo.htmlDir + 'diagram.js')

    pie_rad = 55
    pie_offset = 5
    bar_wid = 80
    bar_hei = 15

    outfile.write('<H1>' + metaInfo.indexPageName['stat'] + '</H1>\n')

    # LinesOfCode
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('Lines of Code')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Lines')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="6" WIDTH="220px"><DIV CLASS="pie_chart">\n')

    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    js += '_BFont="font-family:Verdana;font-weight:bold;font-size:8pt;line-height:10pt;"\n'
    js += 'function initCharts() { for (var i=0;i<4;++i) { MouseOutL(i); MouseOutFS(i); if (i<3) { MouseOutFL(i); MouseOutO(i); MouseOutJ(i); } } MouseOutFS(4); }\n'
    colors = ['#cc3333','#3366ff','#dddddd','#ff9933','#33ff00']
    tcols  = ['#ffffff','#ffffff','#000000','#000000','#000000']
    pieposx = pie_rad + 2*pie_offset
    pieposy = 0
    # pie = PieChart(name,x,y,offset,rad[,colors[]])
    pie = PieChart('L',pieposx,pieposy,pie_offset,pie_rad,colors)
    # pie.addPiece(pct[,tooltip])
    pie.addPiece(metaInfo.getLocPct('code'))
    pie.addPiece(metaInfo.getLocPct('comment'))
    pie.addPiece(metaInfo.getLocPct('empty'))
    pie.addPiece(metaInfo.getLocPct('mixed'))
    js += pie.generate();
    # bar = new ChartLegend(name,x,y,wid,hei,offset[,cols[,tcols]])
    barposx = pieposx + pie_rad + 3*pie_offset
    barposy = pieposy - 2*pie_rad/3
    bar = ChartLegend('L',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    # bar.addBar(text[,tooltip])
    bar.addBar(_('Code'),_('Plain Code'))
    bar.addBar(_('Comment'),_('Plain Comments'))
    bar.addBar(_('Empty'),_('Empty Lines'))
    bar.addBar(_('Mixed'),_('Lines with Code and Comments'))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    for name in ['totals','code','comment','empty','mixed']:
        outfile.write('  <TR><TH CLASS="sub">' + _(name.capitalize()) \
            + '</TH><TD ALIGN="right">' + num_format(metaInfo.getLoc(name)) \
            + '</TD><TD ALIGN="right">' + num_format(metaInfo.getLocPct(name),2) + '%' \
            + '</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # Object Stats
    colors = ['#cc3333','#3366ff','#ff9933','#33ff00','#dddddd']
    posy = 0
    views = 0
    funcs = 0
    procs = 0
    for file_info in metaInfo.fileInfoList:
        views += len(file_info.viewInfoList)
        for package_info in file_info.packageInfoList:
            funcs += len(package_info.functionInfoList)
            procs += len(package_info.procedureInfoList)
    totalObj = views + funcs + procs
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('Object Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" WIDTH="220px" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pie = PieChart('O',pieposx,pieposy,pie_offset,pie_rad,colors)
    pie.addPiece((float(views)/totalObj) * 100)
    pie.addPiece((float(funcs)/totalObj) * 100)
    pie.addPiece((float(procs)/totalObj) * 100)
    js += pie.generate();
    bar = ChartLegend('O',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    bar.addBar(_('Views'))
    bar.addBar(_('Functions'))
    bar.addBar(_('Procedures'))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Views')+'</TH><TD ALIGN="right">'+num_format(views)+'</TD><TD ALIGN="right">'+num_format((float(views)/totalObj) * 100, 2)+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Functions')+'</TH><TD ALIGN="right">'+num_format(funcs)+'</TD><TD ALIGN="right">'+num_format((float(funcs)/totalObj) * 100, 2)+'%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Procedures')+'</TH><TD ALIGN="right">'+num_format(procs)+'</TD><TD ALIGN="right">'+num_format((float(procs)/totalObj) * 100, 2)+'%</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # FileStats
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('File Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" WIDTH="220px"><DIV CLASS="pie_chart">\n')
    totalFiles = metaInfo.getFileStat('files')
    # Lines
    stat = metaInfo.getFileLineStat([400,1000])
    limits = stat.keys() # for some strange reason, sorting gets lost in the dict
    limits.sort()
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pie = PieChart('FL',pieposx,pieposy,pie_offset,pie_rad,colors)
    sum  = (float(stat[400])/totalFiles)*100
    sum2 = (float(stat[1000])/totalFiles)*100
    pie.addPiece(sum)
    pie.addPiece(sum2)
    pie.addPiece(100-(sum+sum2))
    js += pie.generate();
    barposy -= pie_offset
    bar = ChartLegend('FL',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    bar.addBar('&lt; 400',_('less than %s lines') % '400')
    bar.addBar('&lt; '+num_format(1000,0),_('%(from)s to %(to)s'' lines') % {'from': '400', 'to': num_format(1000,0)})
    bar.addBar('&gt; '+num_format(1000,0),_('%s lines and more') % num_format(1000,0))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Total Files')+'</TH><TD ALIGN="right">' + num_format(totalFiles) \
        + '</TD><TD ALIGN="right">' + num_format(100,2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Avg Lines')+'</TH><TD ALIGN="right">' + num_format(metaInfo.getFileStat('avg lines')) \
        + '</TD><TD>&nbsp;</TD></TR>\n')
    havestat = 0
    for limit in limits:
        havestat += stat[limit]
        outfile.write('  <TR><TH CLASS="sub">&lt; ' + num_format(limit,0) + '</TH>' \
            + '<TD ALIGN="right">' + num_format(stat[limit]) + '</TD>' \
            + '<TD ALIGN="right">' + num_format((float(stat[limit])/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">&gt; '+num_format(1000)+'</TH><TD ALIGN="right">' + num_format(totalFiles - havestat) \
        + '</TD><TD ALIGN="right">' + num_format((float(totalFiles - havestat)/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Shortest')+'</TH><TD ALIGN="right">' \
        + num_format(metaInfo.getFileStat('min lines')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Longest')+'</TH><TD ALIGN="right">' \
        + num_format(metaInfo.getFileStat('max lines')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH COLSPAN="4" CLASS="sub delim">&nbsp;</TH></TR>\n')
    # Sizes
    stat = metaInfo.getFileSizeStat([10240,25*1024,50*1024,102400])
    limits = stat.keys() # for some strange reason, sorting gets lost in the dict
    limits.sort()
    outfile.write('  <TR><TH CLASS="sub">'+_('Total Bytes')+'</TH><TD ALIGN="right">' + size_format(metaInfo.getFileStat('sum bytes')) \
        + '</TD><TD ALIGN="right">' + num_format(100,2) + '%</TD><TD COLSPAN="9" WIDTH="220px"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pieposy = pie_rad + pie_offset + bar_hei
    sum  = 0
    cols = ['codecol','commcol','mixcol','emptcol','lastcol']
    pie = PieChart('FS',pieposx,pieposy,pie_offset,pie_rad,colors)
    for limit in limits:
        pie.addPiece((float(stat[limit])/totalFiles)*100)
        sum += (float(stat[limit])/totalFiles)*100
    pie.addPiece(100-sum)
    js += pie.generate();
    barposy = pieposy - 2*pie_rad/3 -2*pie_offset
    bar = ChartLegend('FS',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    oldlim = '0K'
    for limit in limits:
        bar.addBar('&lt; '+size_format(limit,0),_('Files between %(from)s and %(to)s') % {'from': oldlim, 'to': size_format(limit,0)})
        oldlim = size_format(limit,0)
    bar.addBar('&gt; '+size_format(102400,0),_('Files larger than %s') % size_format(102400,0))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Avg Bytes')+'</TH><TD ALIGN="right">' + size_format(metaInfo.getFileStat('avg bytes')) \
        + '</TD><TD>&nbsp;</TD></TR>\n')
    havestat = 0
    for limit in limits:
        havestat += stat[limit]
        outfile.write('  <TR><TH CLASS="sub">&lt; ' + size_format(limit,0) + '</TH>' \
            + '<TD ALIGN="right">' + num_format(stat[limit]) + '</TD>' \
            + '<TD ALIGN="right">' + num_format((float(stat[limit])/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">&gt; '+size_format(102400,0)+'</TH><TD ALIGN="right">' + num_format(totalFiles - havestat) \
        + '</TD><TD ALIGN="right">' + num_format((float(totalFiles - havestat)/totalFiles)*100, 2) + '%</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Smallest')+'</TH><TD ALIGN="right">' \
        + size_format(metaInfo.getFileStat('min bytes')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Largest')+'</TH><TD ALIGN="right">' \
        + size_format(metaInfo.getFileStat('max bytes')) + '</TD><TD>&nbsp;</TD></TR>\n')
    outfile.write("</TABLE>\n")

    # JavaDoc
    jwarns = 0
    jbugs  = 0
    jtodo  = 0
    for file_info in metaInfo.fileInfoList:
        for package_info in file_info.packageInfoList:
            jwarns += package_info.verification.taskCount() + package_info.verification.funcCount() + package_info.verification.procCount()
            jbugs += package_info.bugs.taskCount() + package_info.bugs.funcCount() + package_info.bugs.procCount()
            jtodo += package_info.todo.taskCount() + package_info.todo.funcCount() + package_info.todo.procCount()
        #for view_info in file_info.viewInfoList: ###TODO: view_info.verification is not yet set up###
        #    jwarns += view_info.verification.taskCount() + view_info.verification.funcCount() + view_info.verification.procCount()
    totalObj = jwarns + jbugs + jtodo
    outfile.write("<TABLE CLASS='apilist stat'>\n")
    outfile.write('  <TR><TH COLSPAN="4">'+_('JavaDoc Statistics')+'</TH></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" WIDTH="220px" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
    js = '<SCRIPT Language="JavaScript" TYPE="text/javascript">\n'
    pieposy = 0
    pie = PieChart('J',pieposx,pieposy,pie_offset,pie_rad,colors)
    sum  = (float(jwarns)/totalObj) * 100
    sum2 = (float(jbugs)/totalObj) * 100
    pie.addPiece(sum)
    pie.addPiece(sum2)
    pie.addPiece(100-(sum+sum2))
    js += pie.generate();
    barposy = pieposy - 2*pie_rad/3 - pie_offset
    bar = ChartLegend('J',barposx,barposy,bar_wid,bar_hei,pie_offset,colors,tcols)
    bar.addBar(_('Warnings'),_('JavaDoc validation warnings'))
    bar.addBar(_('Bugs'),_('Known Bugs (from your @bug tags)'))
    bar.addBar(_('Todos'),_('Todo items (from your @todo tags)'))
    js += bar.generate()
    js += '</SCRIPT>\n'
    outfile.write(js);
    outfile.write('</DIV></TD></TR>\n')
    outfile.write('  <TR><TH CLASS="sub">'+_('JavaDoc Warnings')+'</TH><TD ALIGN="right">'+num_format(jwarns)+'</TD><TD ALIGN="right">'+num_format((float(jwarns)/totalObj) * 100, 2)+'%</TD></TR>')
    outfile.write('  <TR><TH CLASS="sub">'+_('Known Bugs')+'</TH><TD ALIGN="right">'+num_format(jbugs)+'</TD><TD ALIGN="right">'+num_format((float(jbugs)/totalObj) * 100, 2)+'%</TD></TR>')
    outfile.write('  <TR><TH CLASS="sub">'+_('Todo Items')+'</TH><TD ALIGN="right">'+num_format(jtodo)+'</TD><TD ALIGN="right">'+num_format((float(jtodo)/totalObj) * 100, 2)+'%</TD></TR>')
    outfile.write("</TABLE>\n")

    outfile.write(MakeHTMLFooter('stat'))
    outfile.close()


def MakeFileIndex(objectType):
    """
    Generate HTML index page for all files, ordered by
    path names (filepath) or file names (file)
    @param string objectType either 'file' or 'filepath'
    """

    if objectType not in ['file','filepath']: # unsupported type
        return
    if metaInfo.indexPage[objectType] == '':  # this index is disabled
        return

    if objectType == 'file':
        printProgress(_("Creating filename no path index"))
        html_title = _('Index Of All Files By File Name')
    else:
        printProgress(_("Creating filename by path index"))
        html_title = _('Index Of All Files By Path Name')

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage[objectType]

    filenametuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue
        if objectType == 'file':
            filenametuplelist.append((os.path.split(file_info.fileName)[1].upper(), file_info))
        else:
            filenametuplelist.append((file_info.fileName.upper(), file_info))
    filenametuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(objectType))
    outfile.write("<H1>"+html_title+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    i = 0

    for filenametuple in filenametuplelist:
        file_name = filenametuple[1].fileName
        temp = os.path.split(file_name)[1].replace(".", "_")
        temp += "_" + `filenametuple[1].uniqueNumber` + ".html"
        if objectType == 'file':
            outfile.write("  <TR CLASS='tr"+`i % 2`+"'><TD><A href=\"" + temp + "\">" + os.path.split(file_name)[1])
        else:
            outfile.write("  <TR CLASS='tr"+`i % 2`+"'><TD><A href=\"" + temp + "\">" + file_name[len(metaInfo.topLevelDirectory)+1:])
        outfile.write("</A></TD></TR>\n")
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter(objectType))
    outfile.close()
	

def MakeElemIndex(objectType):
    """
    Generate HTML index page for all package elements of the specified objectType
    @param string objectType one of 'function', 'procedure'
    """

    if objectType not in ['function','procedure']: # not a valid/supported objectType
        return
    if metaInfo.indexPage[objectType] == '':       # index for this objectType is turned off
        return

    printProgress(_('Creating %s index') % _(objectType))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage[objectType]

    objectTupleList = []
    for file_info in fileInfoList:
        if file_info.fileType != "sql": # skip all non-sql files
            continue
        if objectType == 'function':
            html_title   = _('Index Of All Functions')
            object_name  = _('Function')
        else:
            html_title   = _('Index Of All Procedures')
            object_name  = _('Procedure')
        for package_info in file_info.packageInfoList:
            if objectType == 'function':
                elemInfoList = package_info.functionInfoList
            else:
                elemInfoList = package_info.procedureInfoList
            for elem_info in elemInfoList:
                objectTupleList.append((elem_info.name.upper(), elem_info, file_info, package_info)) # append as tuple for case insensitive sort
    objectTupleList.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(objectType))
    outfile.write("<H1>"+html_title+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_(object_name)+"</TH><TH>"+_('from Package')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Used')+"</TH></TR>\n")
    i = 0

    for object_tuple in objectTupleList: # list of tuples describing every object
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(object_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        # Write column 1: Object name w/ links
        if HTMLjref == '':
            outfile.write("  <TR"+trclass+"><TD>" + object_tuple[1].name.lower())
            if metaInfo.includeSource:
                outfile.write(" <SUP><A href=\"" + HTMLref + "\">#</A></SUP>")
            outfile.write("</TD>")
        else:
            outfile.write("  <TR"+trclass+"><TD>" + object_tuple[1].javadoc.getVisibility() + "<A HREF='" + HTMLjref + "'>" + object_tuple[1].name.lower() + "</A>")
            if metaInfo.includeSource:
                outfile.write(" <SUP><A href=\"" + HTMLref + "\">#</A></SUP>")
            outfile.write("</TD>")
        # Write column 2: Package name w/ links
        outfile.write("<TD>")
        if HTMLpjref == '': # object_tuple[3] is package_info
            outfile.write(object_tuple[3].name.lower())
            if metaInfo.includeSource:
                outfile.write(" <SUP><A HREF='" + HTMLpref + "'>#</A>")
        else:
            outfile.write("<A HREF='" + HTMLpjref + "'>" + object_tuple[3].name.lower() + "</A>")
            if metaInfo.includeSource:
                outfile.write(" <SUP><A HREF='" + HTMLpref + "'>#</A>")
        outfile.write("</TD>")
        # Write column 3: Short description
        outfile.write("<TD>" + object_tuple[1].javadoc.getShortDesc() + "</TD>")
        # Write column 4: where_used
        if len(object_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `object_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD CLASS='whereused'><A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A></TD>\n")
        else:
            outfile.write("<TD>"+_('no use found')+"</TD>")
        outfile.write("</TR>\n")
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter(objectType))
    outfile.close()


def MakeViewIndex():
    """Generate HTML index page for all views"""

    if metaInfo.indexPage['view'] == '':
        return

    printProgress(_("Creating view index"))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage['view']

    viewtuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for view_info in file_info.viewInfoList:
            viewtuplelist.append((view_info.name.upper(), view_info, file_info)) # append as tuple for case insensitive sort

    viewtuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader('view'))
    outfile.write("<H1>"+_('Index Of All Views')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_('View')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Used')+"</TH></TR>\n")
    i = 0

    for view_tuple in viewtuplelist: # list of tuples describing every view
        # file name and line number as an HTML reference
        trclass = ' CLASS="tr'+`i % 2`+'"'
        if metaInfo.includeSource:
            HTMLref = os.path.split(view_tuple[2].fileName)[1].replace(".", "_")
            HTMLref += "_" + `view_tuple[2].uniqueNumber` + ".html"
            HTMLref += "#" + `view_tuple[1].lineNumber`
            outfile.write("  <TR"+trclass+"><TD><A href=\"" + HTMLref + "\">" + view_tuple[1].name.lower() + "</A></TD>")
        else:
            outfile.write("  <TR"+trclass+"><TD>" + view_tuple[1].name.lower() + "</TD>")
        outfile.write("<TD>" + view_tuple[1].javadoc.getShortDesc() + "</TD>")

        if len(view_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `view_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD CLASS='whereused'><A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A></TD>")
        else:
            outfile.write("<TD>"+_('no use found')+"</TD>")
        outfile.write("</TR>\n")
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter('view'))
    outfile.close()


def MakeTaskList(taskType):
    """
    Generate HTML page for all tasks of the specified type found in JavaDoc comments
    @param string taskType Type of the task - one of 'bug', 'todo'
    """

    if taskType not in ['bug','todo','report']:
        return

    if metaInfo.indexPage[taskType] == '':
        return

    printProgress(_("Creating %s list") % _(taskType))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage[taskType]

    packagetuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader(taskType))
    if taskType == 'bug':
        outfile.write("<H1>"+_('List of open Bugs')+"</H1>\n")
    elif taskType == 'todo':
        outfile.write("<H1>"+_('List of things ToDo')+"</H1>\n")
    else:
        outfile.write("<H1>"+_('JavaDoc Validation Report')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")

    # Walk the packages
    for package_tuple in packagetuplelist: # list of tuples describing every package file name and line number as an HTML reference
        if taskType == 'bug':
            task = package_tuple[1].bugs
        elif taskType == 'todo':
            task = package_tuple[1].todo
        else:
            task = package_tuple[1].verification
        if task.allItemCount() < 1:
            continue
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        outfile.write("  <TR><TH COLSPAN='2'><A HREF='" + HTMLjref + "'>" + package_tuple[1].name.lower() + "</A>")
        if metaInfo.includeSource:
            outfile.write(" <SUP><A href=\"" + HTMLref + "\">#</A></SUP>")
        outfile.write("</TH></TR>\n");
        if task.taskCount() > 0:
            outfile.write("  <TR><TD COLSPAN='2' ALIGN='center'><B><I>"+_('Package General')+"</I></B></TD></TR>\n")
            outfile.write("  <TR><TD COLSPAN='2'>" + task.getHtml() + "</TD></TR>\n")
        if task.funcCount() > 0:
            outfile.write("  <TR><TD COLSPAN='2' ALIGN='center'><B><I>"+_('Functions')+"</I></B></TD></TR>\n")
            outfile.write( task.getFuncHtml() )
        if task.procCount() > 0:
            outfile.write("  <TR><TD COLSPAN='2' ALIGN='center'><B><I>"+_('Procedures')+"</I></B></TD></TR>\n")
            outfile.write( task.getProcHtml() )
        outfile.write("  <TR><TD COLSPAN='2'><DIV CLASS='toppagelink'><A HREF='#topOfPage'>"+_('^ Top')+"</A></DIV></TD></TR>\n")

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter(taskType))
    outfile.close()


def MakePackageIndex():
    """Generate HTML index page for all packages"""

    if metaInfo.indexPage['package'] == '':
        return

    printProgress(_("Creating package index"))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage['package']

    packagetuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader('package'))
    outfile.write("<H1>"+_('Index Of All Packages')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_('Package')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Used')+"</TH></TR>\n")
    i = 0

    for package_tuple in packagetuplelist: # list of tuples describing every package file name and line number as an HTML reference
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        if HTMLjref == '':
            outfile.write("  <TR"+trclass+"><TD>" + package_tuple[1].name.lower())
            if metaInfo.includeSource:
                outfile.write(" <SUP><A href=\"" + HTMLref + "\">#</A></SUP>")
            outfile.write("</TD>")
        else:
            outfile.write("  <TR"+trclass+"><TD><A HREF='" + HTMLjref + "'>" + package_tuple[1].name.lower() + "</A>")
            if metaInfo.includeSource:
                outfile.write(" <SUP><A href=\"" + HTMLref + "\">#</A></SUP>")
            outfile.write("</TD>")
        outfile.write("<TD>" + package_tuple[1].javadoc.getShortDesc() + "</TD>")
        if len(package_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write("<TD CLASS='whereused'><A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A></TD></TR>\n")
        else:
            outfile.write("<TD CLASS='whereused'>"+_('no use found')+"</TD></TR>\n")
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter('package'))
    outfile.close()


def MakePackagesWithFuncsAndProcsIndex():
    """Generate HTML index page for all packages, including their functions and procedures"""

    if metaInfo.indexPage['package_full'] == '':
        return

    def WriteObjectList(oTupleList, listName, objectName):
        oTupleList.sort(TupleCompareFirstElements)
        if len(oTupleList) != 0:
            outfile.write("  <TR><TH class='sub' COLSPAN='3'>" + listName + "</TH></TR>\n  <TR><TD COLSPAN='3'>")
            outfile.write("<TABLE ALIGN='center'>\n")
            outfile.write("    <TR><TD ALIGN='center'><B>" + objectName + "</B></TD><TD ALIGN='center'><B>Details</B></TD><TD ALIGN='center'><B>Used</B></TD></TR>\n")
        i = 0
        for oTuple in oTupleList:
            HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(oTuple)
            outfile.write("    <TR CLASS='tr"+`i % 2`+"'><TD>" + oTuple[1].javadoc.getVisibility())
            if HTMLjref == '':
                outfile.write(oTuple[1].name.lower())
            else:
                outfile.write('<A HREF="' + HTMLjref + '">' + oTuple[1].name.lower() + '</A>')
            if metaInfo.includeSource:
                outfile.write(' <SUP><A HREF="' + HTMLref + '">#</A></SUP>')
            outfile.write('</TD>\n')
            outfile.write("<TD>" + oTuple[1].javadoc.getShortDesc() + "</TD>")
            outfile.write("        <TD CLASS='whereused'>")
            if len(oTuple[1].whereUsed.keys()) > 0:
                HTMLwhereusedref = "where_used_" + `oTuple[1].uniqueNumber` + ".html"
                outfile.write("<A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A>")
            else:
                outfile.write(_("no use found"))
            outfile.write("</TD></TR>\n")
            i += 1
        if len(oTupleList) != 0:
            outfile.write("</TABLE></TD></TR>\n")
	    

    printProgress(_("Creating 'package with functions and procedures' index"))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    outfilename = metaInfo.indexPage['package_full']

    packagetuplelist = []
    for file_info in fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = open(html_dir + outfilename, "w")
    outfile.write(MakeHTMLHeader('package_full'))
    outfile.write("<H1>"+_('Index Of All Packages, Their Functions And Procedures')+"</H1>\n")

    for package_tuple in packagetuplelist:
        # file name and line number as an HTML reference
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        outfile.write("<TABLE CLASS='apilist' WIDTH='98%'>\n  <TR><TH COLSPAN='3'>" + package_tuple[1].name.lower() + "</TH></TR>\n")
        outfile.write("  <TR><TD ALIGN='center' WIDTH='33.33%'>")
        if metaInfo.includeSource:
            outfile.write("<A href=\"" + HTMLref + "\">"+_('Code')+"</A>")
        else:
            outfile.write("&nbsp;")
        outfile.write("</TD><TD ALIGN='center' WIDTH='33.34%'>")
        if HTMLjref == '':
            outfile.write("&nbsp;")
        else:
            outfile.write("<A HREF='" + HTMLjref + "'>"+_('ApiDoc')+"</A>")
        outfile.write("</TD><TD CLASS='whereused' WIDTH='33.33%'>")
        if len(package_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write("<A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A>")
        else:
            outfile.write(_("no use found"))
        outfile.write("</TD></TR>\n")

        # functions in this package
        functiontuplelist = []
        for function_info in package_tuple[1].functionInfoList:
            functiontuplelist.append((function_info.name.upper(), function_info, package_tuple[2])) # append as tuple for case insensitive sort
        WriteObjectList(functiontuplelist, _('Functions'), _('Function'))

        # procedures in this package
        proceduretuplelist = []
        for procedure_info in package_tuple[1].procedureInfoList:
            proceduretuplelist.append((procedure_info.name.upper(), procedure_info, package_tuple[2])) # append as tuple for case insensitive sort
        WriteObjectList(proceduretuplelist, _('Procedures'), _('Procedure'))

        outfile.write("</TABLE>\n")

    outfile.write(MakeHTMLFooter('package_full'))
    outfile.close()


def CreateHyperlinkedSourceFilePages():
    """
    Generates pages with the complete source code of each file, including link
    targets (A NAME=) for each line. This way we can link directly to the line
    starting the definition of an object, or where it is called (used) from.
    Very basic syntax highlighting is performed here as well if code is included.
    """
    def ObjectDetailsListItem(item,i):
        """
        Write the row for the overview
        @param object item procedure/function item
        @param int i counter for odd/even row alternation
        """
        iname = item.javadoc.getVisibility()
        if item.javadoc.name != '':
            iname += '<A HREF="#'+item.javadoc.name+'_'+str(item.uniqueNumber)+'">'+item.javadoc.name+'</A>'
            idesc = item.javadoc.getShortDesc()
        else:
            iname += item.name
            idesc = ''
        outfile.write(' <TR CLASS="tr'+`i % 2`+'"><TD><DIV STYLE="margin-left:15px;text-indent:-15px;">'+iname)
        if metaInfo.includeSource:
            outfile.write(' <SUP><A HREF="#'+str(item.lineNumber)+'">#</A></SUP>')
        outfile.write(' (')
        if len(item.javadoc.params) > 0:
            ph = ''
            for par in item.javadoc.params:
                ph += ', ' + par.name
            outfile.write(ph[2:])
        outfile.write(')</DIV></TD><TD>'+idesc+'</TD>')
        if len(item.whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `item.uniqueNumber` + ".html"
            outfile.write("<TD CLASS='whereused'><A href=\"" + HTMLwhereusedref + "\">"+_('where used')+"</A></TD>")
        else:
            outfile.write("<TD CLASS='whereused'>"+_('no use found')+"</TD>")
        outfile.write('</TR>\n')


    printProgress(_("Creating hyperlinked source file pages"))

    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    top_level_directory = metaInfo.topLevelDirectory

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
        dotProgress(dot_count)
        dot_count += 1

        # read up the source file
        infile = open(file_info.fileName, "r")
        infile_line_list = infile.readlines()
        infile.close()

        # generate a file name for us to write to (+1 for delimiter)
        outfilename = os.path.split(file_info.fileName)[1].replace(".", "_")
        outfilename += "_" + `file_info.uniqueNumber` + ".html"

        outfile = open(html_dir + outfilename, "w")
        outfile.write(MakeHTMLHeader(file_info.fileName[len(top_level_directory)+1:]))
        outfile.write("<H1>" + file_info.fileName[len(top_level_directory)+1:] + "</H1>\n")

        # ===[ JAVADOC STARTS HERE ]===
        # Do we have views in this file?
        viewdetails = '\n\n'
        #if len(file_info.viewInfoList) > 0:
            #print 'We have views here'
            ###TODO Do we have to introduce JavaDoc here as well? # *!*

        # Do we have packages in this file?
        packagedetails = '\n\n'
        if len(file_info.packageInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Package Overview')+'</H2>\n')
            outfile.write('<TABLE CLASS="apilist">\n')
            for p in range(len(file_info.packageInfoList)):
                jdoc = file_info.packageInfoList[p].javadoc
                outfile.write(' <TR><TH COLSPAN="3">' + file_info.packageInfoList[p].name + '</TH></TR>\n')
                outfile.write(' <TR><TD COLSPAN="3">')
                outfile.write( jdoc.getHtml(0) )
                outfile.write('</TD></TR>\n')
                # Check the packages for functions
                if len(file_info.packageInfoList[p].functionInfoList) > 0:
                    packagedetails += '<A NAME="funcs"></A><H2>'+_('Functions')+'</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Functions')+'</TH></TR>\n')
                    i = 0
                    for item in file_info.packageInfoList[p].functionInfoList:
                        ObjectDetailsListItem(item,i)
                        packagedetails += item.javadoc.getHtml(item.uniqueNumber)
                        i += 1
                # Check the packages for procedures
                if len(file_info.packageInfoList[p].procedureInfoList) > 0:
                    packagedetails += '<A NAME="procs"></A><H2>'+_('Procedures')+'</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Procedures')+'</TH></TR>\n')
                    i = 0
                    for item in file_info.packageInfoList[p].procedureInfoList:
                        ObjectDetailsListItem(item,i)
                        packagedetails += item.javadoc.getHtml(item.uniqueNumber)
                        i += 1
            outfile.write('</TABLE>\n\n')

        outfile.write(viewdetails)
        outfile.write(packagedetails)
        # ===[ JAVADOC END ]===

        # include the source itself
        if metaInfo.includeSource:
            outfile.write('\n<H2>'+_('Source')+'</H2>\n')
            outfile.write('<code><pre>')
            outfile.write( hypercode(infile_line_list, sqlkeywords, sqltypes) )
            outfile.write("</pre></code>\n")
            outfile.write('<DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV><BR>\n')
            outfile.write(MakeHTMLFooter(file_info.fileName[len(top_level_directory)+1:]))

        outfile.close()

    # print carriage return after last dot
    dotFlush()


def CreateIndexPage():
    """Generates the main index page"""
    printProgress(_("Creating site index page"))

    html_dir = metaInfo.htmlDir
    script_name = metaInfo.scriptName

    outfile = open(html_dir + 'index.html', "w")
    outfile.write(MakeHTMLHeader('Index'))

    # Copy the StyleSheet
    if os.path.exists(metaInfo.css_file):
      copy2(metaInfo.css_file,html_dir + os.path.split(metaInfo.css_file)[1])

    outfile.write("<H1 STYLE='margin-top:100px'>" + metaInfo.title_prefix + " "+_('HyperSQL Reference')+"</H1>\n")

    outfile.write("<BR><BR>\n")
    outfile.write("<TABLE ID='projectinfo' ALIGN='center'><TR><TD VALIGN='middle' ALIGN='center'>\n")
    if metaInfo.projectLogo != '':
      logoname = os.path.split(metaInfo.projectLogo)[1]
      copy2(metaInfo.projectLogo,html_dir + logoname)
      outfile.write("  <IMG ALIGN='center' SRC='" + logoname + "' ALT='Logo'><BR><BR><BR>\n")
    outfile.write(metaInfo.projectInfo)
    outfile.write("</TD></TR></TABLE>\n")
    outfile.write("<BR><BR>\n")

    outfile.write(MakeHTMLFooter('Index'))
    outfile.close()


def CreateWhereUsedPages():
    """Generate a where-used-page for each object"""
    printProgress(_("Creating 'where used' pages"))

    html_dir = metaInfo.htmlDir
    fileInfoList = metaInfo.fileInfoList

    # loop through files
    dot_count = 1
    for file_info in fileInfoList:

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

        # print a . every file
        dotProgress(dot_count)
        dot_count += 1
	
        # loop through views
        for view_info in file_info.viewInfoList:

            if len(view_info.whereUsed.keys()) == 0:
                continue
            
            #open a "where used" file
            whereusedfilename = "where_used_" + `view_info.uniqueNumber` + ".html"
            outfile = open(html_dir + whereusedfilename, "w")
            
            # write our header
            outfile.write(MakeHTMLHeader('Index'))
            outfile.write("<H1>" + view_info.name + " "+_('Where Used List')+"</H1>\n")
            outfile.write("<TABLE CLASS='apilist'>\n")
            outfile.write("  <TR><TH>"+_('File')+"</TH><TH>"+_('Line')+"</TH></TR>\n")

            # each where used
            where_used_keys = view_info.whereUsed.keys()
            where_used_keys.sort(CaseInsensitiveComparison)
            for key in where_used_keys:
                for whereusedtuple in view_info.whereUsed[key]:
                    line_number = whereusedtuple[1]
                    unique_number = whereusedtuple[0].uniqueNumber
                    outfile.write("  <TR><TD>")

                    # only make hypertext references for SQL files for now
                    if whereusedtuple[0].fileType == "sql" and metaInfo.includeSource:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                        outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                        outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                        outfile.write( `line_number` + "</A>")
                    else:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

            # footer and close
            outfile.write("</TABLE>")
            outfile.write(MakeHTMLFooter(view_info.name + " "+_('Where Used List')))
            outfile.close()

        for package_info in file_info.packageInfoList:

            if len(package_info.whereUsed.keys()) != 0:
            
                #open a "where used" file
                whereusedfilename = "where_used_" + `package_info.uniqueNumber` + ".html"
                outfile = open(html_dir + whereusedfilename, "w")
            
                # write our header
                outfile.write(MakeHTMLHeader(package_info.name + " "+_("Where Used List")))
                outfile.write("<H1>" + package_info.name + " Where Used List</H1>\n")
                outfile.write("<TABLE CLASS='apilist'>\n")
                outfile.write("  <TR><TH>"+_('File')+"</TH><TH>"+_('Line')+"</TH></TR>\n")

                # each where used
                where_used_keys = package_info.whereUsed.keys()
                where_used_keys.sort(CaseInsensitiveComparison)
                for key in where_used_keys:
                    for whereusedtuple in package_info.whereUsed[key]:
                        line_number = whereusedtuple[1]
                        unique_number = whereusedtuple[0].uniqueNumber
                        outfile.write("  <TR><TD>")

                        # only make hypertext references for SQL files for now
                        if whereusedtuple[0].fileType == "sql" and metaInfo.includeSource:
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                            outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                            outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                            outfile.write(`line_number` + "</A>")
                        else:
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                        outfile.write("</TD></TR>\n")

                # footer and close
                outfile.write("</TABLE>")
                outfile.write(MakeHTMLFooter(package_info.name + " "+_("Where Used List")))
                outfile.close()

            #look for any of this packages' functions
            for function_info in package_info.functionInfoList:
                if len(function_info.whereUsed.keys()) == 0:
                    continue
                
                #open a "where used" file
                whereusedfilename = "where_used_" + `function_info.uniqueNumber` + ".html"
                outfile = open(html_dir + whereusedfilename, "w")
                
                # write our header
                outfile.write(MakeHTMLHeader(function_info.name.lower() + ' '+_('from Package')+' ' + package_info.name))
                outfile.write("<H1>" + function_info.name.lower() + " <I>"+_('from package')+" " + package_info.name)
                outfile.write(" </I>"+_('Where Used List')+"</H1>\n")
                outfile.write("<TABLE CLASS='apilist'>\n")
                outfile.write("  <TR><TH>"+_('File')+"</TH><TH>"+_('Line')+"</TH></TR>\n")

                # each where used
                where_used_keys = function_info.whereUsed.keys()
                where_used_keys.sort(CaseInsensitiveComparison)
                for key in where_used_keys:
                    for whereusedtuple in function_info.whereUsed[key]:
                        line_number = whereusedtuple[1]
                        unique_number = whereusedtuple[0].uniqueNumber

                    # only make hypertext references for SQL files for now
                    outfile.write("  <TR><TD>")
                    if whereusedtuple[0].fileType == "sql" and metaInfo.includeSource:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                        outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                        outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                        outfile.write(`line_number` + "</A>")
                    else:
                        outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

                # footer and close
                outfile.write("</TABLE>")
                outfile.write(MakeHTMLFooter(function_info.name.lower() + ' '+_('from package')+' ' + package_info.name))
                outfile.close()

            #look for any of this packages procedures
            for procedure_info in package_info.procedureInfoList:
                if len(procedure_info.whereUsed.keys()) == 0:
                    continue
                
                #open a "where used" file
                whereusedfilename = "where_used_" + `procedure_info.uniqueNumber` + ".html"
                outfile = open(html_dir + whereusedfilename, "w")
                
                # write our header
                outfile.write(MakeHTMLHeader(procedure_info.name.lower() + ' '+('from package')+' ' + package_info.name.lower()))
                outfile.write("<H1>" + procedure_info.name.lower() + " <I>"+_('from package')+" " + package_info.name.lower())
                outfile.write(" </I>"+_('Where Used List')+"</H1>\n")
                outfile.write("<TABLE CLASS='apilist'>\n")
                outfile.write("  <TR><TH>"+_('File')+"</TH><TH>"+_('Line')+"</TH></TR>\n")
                
                # each where used
                where_used_keys = procedure_info.whereUsed.keys()
                where_used_keys.sort(CaseInsensitiveComparison)
                for key in where_used_keys:
                    for whereusedtuple in procedure_info.whereUsed[key]:
                        line_number = whereusedtuple[1]
                        unique_number = whereusedtuple[0].uniqueNumber
                        outfile.write("  <TR><TD>")

                        # only make hypertext references for SQL files for now
                        if whereusedtuple[0].fileType == "sql" and metaInfo.includeSource:
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>")
                            outfile.write("<A href=\"" + os.path.split(key)[1].replace(".", "_"))
                            outfile.write("_" + `unique_number` + ".html" + "#" + `line_number` + "\">")
                            outfile.write(`line_number` + "</A>")
                        else:
                            outfile.write(key[len(top_level_directory)+1:] + "</TD><TD>" + `line_number`)
                    outfile.write("</TD></TR>\n")

                # footer and close
                outfile.write("</TABLE>")
                outfile.write(MakeHTMLFooter(procedure_info.name.lower() + ' '+_('from package')+' ' + package_info.name.lower()))
                outfile.close()

    # print carriage return after last dot
    dotFlush()


def confPage(page,filenameDefault,pagenameDefault,enableDefault):
    """
    Add the specified page to the list of pages to process if it is enabled
    @param string page index key for the page to setup
    @param string filenameDefault default for the file name (used if not found in config)
    @param string pagenameDefault default for the page name (used if not found in config)
    @param boolean enableDefault
    """
    if config.getBool('Pages',page,enableDefault):
        metaInfo.indexPage[page] = config.get('FileNames',page,filenameDefault)
        metaInfo.indexPageName[page] = config.get('PageNames',page,pagenameDefault)
        metaInfo.indexPageCount += 1
    else:
        metaInfo.indexPage[page] = ''

def configRead():
    """ Setup internal variables from config """
    # Section GENERAL
    metaInfo.title_prefix  = config.get('General','title_prefix','HyperSQL')
    metaInfo.projectInfo   = config.get('General','project_info','')
    infofile               = config.get('General','project_logo_url','')
    if infofile == '':
      metaInfo.projectLogo = config.get('General','project_logo','')
    else:
      metaInfo.projectLogo = infofile
    infofile               = config.get('General','project_info_file','')
    if infofile != '' and os.path.exists(infofile):
        infile = open(infofile, "r")
        fileLines = infile.readlines()
        infile.close()
        for i in range(len(fileLines)):
            metaInfo.projectInfo += fileLines[i]
    metaInfo.encoding     = config.get('General','encoding','utf8')
    JavaDocVars['ticket_url']   = config.get('General','ticket_url','')
    JavaDocVars['wiki_url']     = config.get('General','wiki_url','')
    # Section FILENAMES
    metaInfo.topLevelDirectory  = config.get('FileNames','top_level_directory','.') # directory under which all files will be scanned
    JavaDocVars['top_level_dir_len'] = len(metaInfo.topLevelDirectory)
    metaInfo.rcsnames           = config.getList('FileNames','rcsnames',['RCS','CVS','.svn']) # directories to ignore
    metaInfo.sql_file_exts      = config.getList('FileNames','sql_file_exts',['sql', 'pkg', 'pkb', 'pks', 'pls']) # Extensions for files to treat as SQL
    metaInfo.cpp_file_exts      = config.getList('FileNames','cpp_file_exts',['c', 'cpp', 'h']) # Extensions for files to treat as C
    metaInfo.htmlDir            = config.get('FileNames','htmlDir',os.path.split(sys.argv[0])[0] + os.sep + "html" + os.sep)
    metaInfo.css_file           = config.get('FileNames','css_file','hypersql.css')
    metaInfo.css_url            = config.get('FileNames','css_url','')
    metaInfo.indexPage          = {}
    metaInfo.indexPageCount     = 1 # We at least have the main index page
    metaInfo.indexPageName      = {}
    confPage('filepath','FileNameIndexWithPathnames.html','File Names by Path Index',True)
    confPage('file','FileNameIndexNoPathnames.html','File Name Index',True)
    confPage('view','ViewIndex.html','View Index',False)
    confPage('package','PackageIndex.html','Package Index',True)
    confPage('package_full','PackagesWithFuncsAndProcsIndex.html','Full Package Listing',True)
    confPage('function','FunctionIndex.html','Function Index',True)
    confPage('procedure','ProcedureIndex.html','Procedure Index',True)
    confPage('bug','BugIndex.html','Bug List',True)
    confPage('todo','TodoIndex.html','Todo List',True)
    confPage('report','ReportIndex.html','Verification Report',True)
    confPage('stat','StatIndex.html','Code Statistics',True)
    # Sections PAGES and PAGENAMES are handled indirectly via confPage() in section FileNames
    # Section PROCESS
    metaInfo.blindOffset = abs(config.getInt('Process','blind_offset',0)) # we need a positive integer
    metaInfo.includeSource = config.getBool('Process','include_source',True)
    # Section VERIFICATION
    JavaDocVars['javadoc_mandatory'] = config.getBool('Verification','javadoc_mandatory',False)
    JavaDocVars['verification'] = config.getBool('Verification','verify_javadoc',False)
    JavaDocVars['mandatory_tags'] = config.getList('Verification','mandatory_tags',[])

def confLogger():
    """ Setup logging """
    logging.addLevelName(99,'NONE')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler( config.get('Logging','logfile') )
    ch = logging.StreamHandler()
    #fh.setFormatter( logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s") )
    fh.setFormatter( logging.Formatter("%(asctime)s %(module)s %(levelname)s %(message)s") )
    #ch.setFormatter( logging.Formatter("* %(name)s %(levelname)s %(message)s") )
    ch.setFormatter( logging.Formatter("* %(module)s %(levelname)s %(message)s") )
    try:
        fh.setLevel( eval('logging.'+config.get('Logging','filelevel','WARNING').upper()) )
    except AttributeError:
        fh.setLevel(logging.WARNING)
    try:
        ch.setLevel( eval('logging.'+config.get('Logging','screenlevel','WARNING').upper()) )
    except AttributeError:
        ch.setLevel(logging.ERROR)
    logger.addHandler(fh)
    logger.addHandler(ch)

def printProgress(msg):
    """
    If config(Logging.progress) evaluates to True, print which step we are performing
    @param string msg what to print out
    """
    logger.debug(msg)
    if config.getBool('Logging','progress',True):
        print msg

def dotProgress(dot_count):
    """
    If config(Logging.progress) evaluates to True, print a '.' for each processed object
    (usually for each processed file), plus a line break all 60 dots
    @param int dot_count how many dots have been processed already (for line break)
    """
    if config.getBool('Logging','progress',True):
        sys.stdout.write(".")
        sys.stdout.flush()
        if (dot_count % 60) == 0: # carriage return every 60 dots
            print
            sys.stdout.flush()

def dotFlush():
    """
    If we print progress dots (see dotProgress), we need to close the last line
    """
    if config.getBool('Logging','progress',True):
        print

if __name__ == "__main__":

    # Read configuration
    config = HyperConf()
    config.initDefaults()

    # Check the config files
    confName = []
    scriptpath = os.path.split(sys.argv[0])[0] + os.sep
    for proj in ['HyperSQL','hypersql']:
        if not scriptpath + proj + '.ini' in confName and os.path.exists(scriptpath + proj + '.ini'):
            confName.append(scriptpath + proj + '.ini')
    if len(sys.argv)>1:
        for proj in [sys.argv[1].lower(),sys.argv[1]]:
            if not scriptpath + proj + '.ini' in confName and os.path.exists(scriptpath + proj + '.ini'):
                confName.append(scriptpath + proj + '.ini')
    # If we have any config files, read them!
    if len(confName) > 0:
      config.read(confName)
    else:
      print 'No config file found, using defaults.'

    # Setup gettext
    langs = []
    lc, encoding = locale.getdefaultlocale()
    if (lc):
        langs = [lc]
    language = os.environ.get('LANGUAGE', None)
    if (language):
        langs += language.split(":")
    langs += ['en_US', 'en_EN']
    gettext.bindtextdomain('hypersql', scriptpath + os.sep + 'lang')
    gettext.textdomain('hypersql')
    lang = gettext.translation('hypersql', scriptpath + os.sep + 'lang', languages=langs, fallback=True)
    _ = lang.gettext


    metaInfo = MetaInfo() # This holds top-level meta information, i.e., lists of filenames, etc.
    metaInfo.versionString = "2.3"
    metaInfo.scriptName = sys.argv[0]

    # Initiate logging
    logger = logging.getLogger('main')
    confLogger()
    logger.info(_('HyperSQL v%s initialized') % metaInfo.versionString)
    logger.debug('ScriptName: '+metaInfo.scriptName)
    if len(confName) > 0:
      logger.info(_('Using config file(s) ') + ', '.join(confName))
    else:
      logger.info(_('No config file found, using defaults.'))
    if config.getBool('Process','whereused_scan_shortrefs'):
      logger.info(_('where_used shortref scan enabled'))
    else:
      logger.info(_('where_used shortref scan disabled'))

    configRead()
    top_level_directory = metaInfo.topLevelDirectory
    if not os.path.exists(top_level_directory):
        logger.critical(_('top_level_directory "%s" does not exist - terminating.') % top_level_directory)
        sys.exit(os.EX_OSFILE)

    #
    # Start processing
    #
    #print '====================='
    #print dir(metaInfo)
    #print '====================='
    #sys.exit()

    FindFilesAndBuildFileList(metaInfo.topLevelDirectory, metaInfo.fileInfoList)
    ScanFilesForViewsAndPackages()
    ScanFilesForWhereViewsAndPackagesAreUsed()

    if config.getBool('Process','purge_on_start',False) and os.path.exists(metaInfo.htmlDir):
      printProgress(_("Removing html files from previous run"))
      names=os.listdir(metaInfo.htmlDir)
      for i in names:
        os.unlink(metaInfo.htmlDir + i)

    CreateHTMLDirectory()

    # Generating the index pages
    MakeFileIndex('filepath')
    MakeFileIndex('file')
    MakeViewIndex()
    MakePackageIndex()
    MakeElemIndex('function')
    MakeElemIndex('procedure')
    MakePackagesWithFuncsAndProcsIndex()

    CreateWhereUsedPages()
    CreateHyperlinkedSourceFilePages()
    CreateIndexPage()

    # Bug and Todo lists
    MakeTaskList('bug')
    MakeTaskList('todo')
    MakeTaskList('report')
    MakeStatsPage()

    printProgress(_("done"))
    logger.info('Processed %s total lines: %s empty, %s plain comments, %s plain code, %s mixed', \
        metaInfo.getLoc('totals'), metaInfo.getLoc('empty'), metaInfo.getLoc('comment'), metaInfo.getLoc('code'), \
        metaInfo.getLoc('totals') - metaInfo.getLoc('empty') - metaInfo.getLoc('comment') - metaInfo.getLoc('code'))
    logger.info('Percentage: %s%% empty, %s%% plain comments, %s%% plain code, %s%% mixed', \
        metaInfo.getLocPct('empty'), metaInfo.getLocPct('comment'), metaInfo.getLocPct('code'), \
        metaInfo.getLocPct('mixed'))
    logger.info(_('HyperSQL v%s exiting normally') % metaInfo.versionString)
