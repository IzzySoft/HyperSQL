#!/usr/bin/python
# -*- coding: utf-8 -*-

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
import os, sys, time, fileinput, logging, re, gettext, locale
from shutil import copy2

# now import our own modules
sys.path.insert(0,os.path.split(sys.argv[0])[0] + os.sep + 'lib')
from hypercore import *
from hyperjdoc import *
from hypercode import *
from hyperconf import *
from hyperconf import _ # needs explicit call
from hypercharts import *
from systools import *
from depgraph import *
from progressbar import *
import hypercache

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

    fileInfoList = metaInfo.fileInfoList
    pbarInit(_("Scanning source files for views and packages"),0,len(fileInfoList))
    i = 0
    strpatt = re.compile("('[^']*')+")    # String-Regexp

    # first, find views in files
    dot_count = 1
    for file_info in fileInfoList:

        # print a . every file
        i += 1
        pbarUpdate(i)

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

        infile = fopen(file_info.fileName, "r", metaInfo.encoding)
        fileLines = infile.readlines()
        infile.close()
        file_info.lines = len(fileLines)
        file_info.bytes  = os.path.getsize(file_info.fileName)

        # scan this file for possible JavaDoc style comments
        if metaInfo.useJavaDoc:
            jdoc = ScanJavaDoc(fileLines, file_info.fileName)
        else:
            jdoc = []

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
                        #for mand in mands: Need to setup report here as well! ###TODO### also: handle @ignore
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
                    if not package_info.javadoc.ignore: # ignore items with @ignore tag
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
                        ###TODO:### Shouldn't the following two items be in the outer loop to avoid duplicate processing of overloaded functions?
                        if len(jdoc[j].bug) > 0 and metaInfo.indexPage['bug'] != '':
                            for ib in range(len(jdoc[j].bug)):
                                file_info.packageInfoList[package_count].bugs.addFunc(jdoc[j].name,jdoc[j].bug[ib])
                        if len(jdoc[j].todo) > 0 and metaInfo.indexPage['todo'] != '':
                            for ib in range(len(jdoc[j].todo)):
                                file_info.packageInfoList[package_count].todo.addFunc(jdoc[j].name,jdoc[j].todo[ib])
                    if not function_info.javadoc.ignore:
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
                    if not procedure_info.javadoc.ignore:
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

    # complete line on task completion
    pbarClose()


def ScanFilesForWhereViewsAndPackagesAreUsed():
    """
    Scans files collected in metaInfo.fileInfoList and checks them line by line
    with metaInfo.<object>list for calls to those objects. If it finds any, it
    updates <object>list where_used property accordingly.
    """

    def findUsingObject(fInfo,lineNumber):
        vObj = ElemInfo()
        pObj = ElemInfo()
        fObj = ElemInfo()
        PObj = PackageInfo()
        if len(fInfo.viewInfoList)!=0:
            for vInfo in fInfo.viewInfoList:
                if vInfo.lineNumber < lineNumber: vObj = vInfo
                else: break
        if len(fInfo.packageInfoList)!=0:
            for pInfo in fInfo.packageInfoList:
                if pInfo.lineNumber < lineNumber: PObj = pInfo
                for vInfo in pInfo.functionInfoList:
                    if vInfo.lineNumber < lineNumber: fObj = vInfo
                    else: break
                for vInfo in pInfo.procedureInfoList:
                    if vInfo.lineNumber < lineNumber: pObj = vInfo
                    else: break
        sobj = [['view',vObj.lineNumber,vObj],['pkg',PObj.lineNumber,PObj],['func',fObj.lineNumber,fObj],['proc',pObj.lineNumber,pObj]]
        sobj.sort(key=lambda obj: obj[1], reverse=True)
        if sobj[0][1] < 0: rtype = 'file' # No object found
        else: rtype = sobj[0][0]
        return rtype,sobj[0][2]
        

    # colors for the depgraph
    if metaInfo.indexPage['depgraph']:
        cols = {}
        cols['proc'] = ['#ff9933','#000000']
        cols['view'] = ['#cc3333','#ffffff']
        cols['func'] = ['#3366ff','#ffffff']
        cols['pkg']  = ['#33ff00','#000000']

    def addWhereUsed(objectInfo,fileInfo,lineNumber,otype):
        """
        Add where_used info to an object (view, procedure, function, ...)
        @param object objectInfo the view_info/function_info/... object used there
        @param object fileInfo object of the file where the usage was found
        @param int lineNumber file line number where the usage was found
        @param string otype object type of the used object
        """
        uType,uObj = findUsingObject(fileInfo,lineNumber)
        if fileInfo.fileName not in objectInfo.whereUsed.keys():
            objectInfo.whereUsed[fileInfo.fileName] = []
        objectInfo.whereUsed[fileInfo.fileName].append((fileInfo, lineNumber, uType, uObj))
        # generate a unique number for use in making where used file if needed
        if objectInfo.uniqueNumber == 0:
            objectInfo.uniqueNumber = metaInfo.NextIndex()
        # now care for the what_used
        if uType != 'file':
            if otype in ['view','pkg']:
                fname = objectInfo.parent.fileName
                finfo = objectInfo.parent
            elif otype in ['func','proc']:
                try:
                    fname = objectInfo.parent.parent.fileName
                    finfo = objectInfo.parent.parent
                except:
                    try:
                        fname = objectInfo.parent.fileName
                        finfo = objectInfo.parent
                    except:
                        logger.warn(_('Could not find filename for %(otype)s %(name)s'), {'otype':otype, 'name':objectInfo.name})
                        fname = fileInfo.fileName
                        finfo = fileInfo
            else:
                fname = fileInfo.fileName
                finfo = fileInfo
            if fname not in uObj.whatUsed.keys():
                uObj.whatUsed[fname] = []
            uObj.whatUsed[fname].append((finfo, objectInfo.lineNumber, otype, objectInfo))
            if uObj.uniqueNumber == 0: uObj.uniqueNumber = metaInfo.NextIndex()
            if uType in ['func','proc'] and hasattr(uObj.parent,'whatUsed'): # add the info to pkg as well
                if finfo.fileName not in uObj.parent.whatUsed.keys():
                    uObj.parent.whatUsed[finfo.fileName] = []
                uObj.parent.whatUsed[finfo.fileName].append((finfo, objectInfo.lineNumber, otype, objectInfo))
                if uObj.parent.uniqueNumber == 0: uObj.parent.uniqueNumber = metaInfo.NextIndex()
        # handle depgraph info
        if metaInfo.indexPage['depgraph'] and otype in metaInfo.depGraphObjects \
          and not objectInfo.javadoc.private and not uObj.javadoc.private:
            # basic: file -> file
            if otype in ['proc','func'] and objectInfo.parent: oto = objectInfo.parent.parent.fileName
            else: oto = objectInfo.parent.fileName
            oto = os.path.split(oto)[1]
            ofrom = os.path.split(fileInfo.fileName)[1]
            dep = '"' + ofrom + '" -> "' + oto + '";'
            if not dep in metaInfo.depGraph['file2file']:
                metaInfo.depGraph['file2file'].append(dep)
            # medium: object -> file
            if uType in ['proc','func'] and uObj.parent: uname = uObj.parent.name.lower() + '.' + uObj.name.lower()
            else: uname = uObj.name.lower()
            dep = '"' + uname + '" -> "' + oto + '";'
            if not dep in metaInfo.depGraph['object2file']:
                metaInfo.depGraph['object2file'].append(dep)
                props = '"' + uname + '" [color="'+cols[uType][0]+'",fontcolor="'+cols[uType][1] + '"];'
                if not props in metaInfo.depGraph['object2file']:
                    metaInfo.depGraph['object2file'].append(props)
            # medium: file -> object
            if otype in ['proc','func']: oto = objectInfo.parent.name.lower() + '.' + objectInfo.name.lower()
            else: oto = objectInfo.name.lower()
            dep = '"' + ofrom + '" -> "' + oto + '";'
            if not dep in metaInfo.depGraph['file2object']:
                metaInfo.depGraph['file2object'].append(dep)
                props = '"' + uname + '" [color="'+cols[uType][0]+'",fontcolor="'+cols[uType][1] + '"];'
                if not props in metaInfo.depGraph['file2object']:
                    metaInfo.depGraph['file2object'].append(props)
            # full: object -> object
            if otype in ['proc','func'] and objectInfo.parent: oname = objectInfo.parent.name.lower() + '.' + objectInfo.name.lower()
            else: oname = objectInfo.name.lower()
            dep = '"' + uname + '" -> "' + oname + '";'
            if not dep in metaInfo.depGraph['object2object']:
                metaInfo.depGraph['object2object'].append(dep)
                props = '"' + uname + '" [color="'+cols[uType][0]+'",fontcolor="'+cols[uType][1] + '"];'
                if not props in metaInfo.depGraph['object2object']:
                    metaInfo.depGraph['object2object'].append(props)
                props = '"' + oname + '" [color="'+cols[otype][0]+'",fontcolor="'+cols[otype][1] + '"];'
                if not props in metaInfo.depGraph['object2object']:
                    metaInfo.depGraph['object2object'].append(props)


    fileInfoList = metaInfo.fileInfoList

    pbarInit(_("Scanning source files for where views and packages are used"),0,len(fileInfoList))
    scan_instring = config.getBool('Process','whereused_scan_instring')
    if scan_instring:
        logger.info(_('Including strings in where_used scan'))
    else:
        logger.info(_('Excluding strings from where_used scan'))
        strpatt = re.compile("('[^']*')+")    # String-Regexp

    outerfileInfoList = []
    for file_info in fileInfoList:
        outerfileInfoList.append(file_info)

    i = 0
    for outer_file_info in outerfileInfoList:
        # update progressbar
        i += 1
        pbarUpdate(i)

        infile = fopen(outer_file_info.fileName, "r", metaInfo.encoding)
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
                        if re.search('\\b'+view_info.name+'\\b',fileLines[lineNumber],re.I):
                            addWhereUsed(view_info, outer_file_info, lineNumber, 'view')


                # if this FileInfo instance has packages
                if len(inner_file_info.packageInfoList) != 0:
                    for package_info in inner_file_info.packageInfoList:

                        # perform case insensitive find, this is "package name"."function or procedure name"
                        if re.search('\\b'+package_info.name+'\.',fileLines[lineNumber],re.I):
                            addWhereUsed(package_info, outer_file_info, lineNumber, 'pkg')

                            #look for any of this packages' functions
                            for function_info in package_info.functionInfoList:
                                # perform case insensitive find
                                if re.search('\\b'+package_info.name+'\.'+function_info.name+'\\b',fileLines[lineNumber],re.I):
                                    addWhereUsed(function_info, outer_file_info, lineNumber, 'func')

                            #look for any of this packages procedures
                            for procedure_info in package_info.procedureInfoList:
                                # perform case insensitive find
                                if re.search('\\b'+package_info.name+'\.'+procedure_info.name+'\\b',fileLines[lineNumber],re.I):
                                    addWhereUsed(procedure_info, outer_file_info, lineNumber, 'proc')

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
                                    addWhereUsed(function_info, outer_file_info, lineNumber, 'func')

                            #look for any of this packages procedures
                            for procedure_info in package_info.procedureInfoList:
                                # perform case insensitive find
                                if fileLines[lineNumber].upper().find(procedure_info.name.upper(),0,epos) != -1 \
                                 and (fileLines[lineNumber].upper().find(" " + procedure_info.name.upper(),0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(procedure_info.name.upper(),0,epos) == 0) \
                                 and (fileLines[lineNumber].upper().find(procedure_info.name.upper()+" ",0,epos) != -1 \
                                  or fileLines[lineNumber].upper().find(procedure_info.name.upper()+"(",0,epos) != -1):
                                    addWhereUsed(procedure_info, outer_file_info, lineNumber, 'proc')


    # complete line on task completion
    pbarClose()


def MakeNavBar(current_page):
    """
    Generates HTML code for the general navigation links to all the index pages
    The current page will be handled separately (no link, highlight)
    @param string current_page name of the current page
    """
    itemCount = 0
    s = "<TABLE CLASS='topbar' WIDTH='98%'><TR>\n"
    s += "  <TD CLASS='navbar'>\n"
    for item in ['package','function','procedure','package_full','view','file','filepath','bug','todo','report','stat','depgraph']:
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

def makeDualCodeRef(href,jref,name):
    """
    Create the anchor element to the object details
    @param string href code URL
    @param string jref JavaDoc URL
    @param string name Name of the object
    @return string anchor HTML A element or plain text (if no refs - unlikely,
            only possible if include_source==0 and javadoc==0)
    """
    if metaInfo.useJavaDoc:
        if jref=='':
            anchor = name
        else:
            anchor = '<A HREF="'+jref+'">'+name+'</A>'
        if href[0]!='' and metaInfo.includeSource:
            anchor += ' <SUP><A HREF="'+href+'">#</A></SUP>'
    else:
        if href[0]=='' or not metaInfo.includeSource:
            anchor = name
        else:
            anchor = '<A HREF="'+href+'">'+name+'</A>'
    return anchor

def MakeStatsPage():
    """
    Generate Statistics Page
    """

    if metaInfo.indexPage['stat'] == '': # statistics disabled
        return

    printProgress(_('Creating statistics page'))

    outfile = fopen(metaInfo.htmlDir + metaInfo.indexPage['stat'], 'w', metaInfo.encoding)
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
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Lines')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="6" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')

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
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
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
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')
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
        + '</TD><TD ALIGN="right">' + num_format(100,2) + '%</TD><TD COLSPAN="9" CLASS="pie_chart"><DIV CLASS="pie_chart">\n')
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
    outfile.write('  <TR><TH CLASS="sub">'+_('Name')+'</TH><TH CLASS="sub">'+_('Value')+'</TH><TH CLASS="sub">'+_('Pct')+'</TH><TD ROWSPAN="8" CLASS="pie_chart" STYLE="height:120px;"><DIV CLASS="pie_chart">\n')
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader(objectType))
    outfile.write("<H1>"+html_title+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_(object_name)+"</TH><TH>"+_('from Package')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Used')+"</TH></TR>\n")
    i = 0

    for object_tuple in objectTupleList: # list of tuples describing every object
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(object_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        # Write column 1: Object name w/ links
        outfile.write("  <TR"+trclass+"><TD>" + object_tuple[1].javadoc.getVisibility() + makeDualCodeRef(HTMLref,HTMLjref,object_tuple[1].name.lower()) + "</TD>")
        # Write column 2: Package name w/ links
        outfile.write("<TD>" + makeDualCodeRef(HTMLpref,HTMLpjref,object_tuple[3].name.lower()) + "</TD>")
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
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
        outfile.write('  <TR><TH COLSPAN="2">' + makeDualCodeRef(HTMLref,HTMLjref,package_tuple[1].name.lower()) + "</TH></TR>\n");
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader('package'))
    outfile.write("<H1>"+_('Index Of All Packages')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_('Package')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Usage')+"</TH></TR>\n")
    i = 0

    for package_tuple in packagetuplelist: # list of tuples describing every package file name and line number as an HTML reference
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        outfile.write('  <TR'+trclass+'><TD>' + makeDualCodeRef(HTMLref,HTMLjref,package_tuple[1].name.lower()) + '</TD>')
        outfile.write("<TD>" + package_tuple[1].javadoc.getShortDesc() + "</TD><TD CLASS='whereused'>")
        if len(package_tuple[1].whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write('<A href="' + HTMLwhereusedref + '">' + _('where used') + '</A> / ')
        else:
            outfile.write('- / ')
        if len(package_tuple[1].whatUsed.keys()) > 0:
            HTMLwhatusedref = "what_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write('<A href="' + HTMLwhatusedref + '">' + _('what used') + '</A>')
        else:
            outfile.write('-')
        outfile.write('</TD></TR>\n')
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
            outfile.write("    <TR><TD ALIGN='center'><B>" + objectName + "</B></TD><TD ALIGN='center'><B>Details</B></TD><TD ALIGN='center'><B>"+_('Usage')+"</B></TD></TR>\n")
        i = 0
        for oTuple in oTupleList:
            HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(oTuple)
            outfile.write("    <TR CLASS='tr"+`i % 2`+"'><TD>" + oTuple[1].javadoc.getVisibility() \
              + makeDualCodeRef(HTMLref,HTMLjref, oTuple[1].name.lower()) + '</TD>\n')
            outfile.write("<TD>" + oTuple[1].javadoc.getShortDesc() + "</TD>")
            outfile.write("        <TD CLASS='whereused'>")
            if len(oTuple[1].whereUsed.keys()) > 0:
                HTMLwhereusedref = "where_used_" + `oTuple[1].uniqueNumber` + ".html"
                outfile.write('<A href="' + HTMLwhereusedref + '">'+_('where used')+'</A> /')
            else:
                outfile.write("- /")
            if len(oTuple[1].whatUsed.keys()) > 0:
                HTMLwhatusedref = "what_used_" + `oTuple[1].uniqueNumber` + ".html"
                outfile.write('<A href="' + HTMLwhatusedref + '">'+_('what used')+'</A>')
            else:
                outfile.write("-")
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

    outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
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
            outfile.write('<A href="' + HTMLwhereusedref + '">'+_('where used')+'</A> / ')
        elif len(package_tuple[1].whatUsed.keys()) > 0:
            outfile.write('- / ')
        else:
            outfile.write(_("no use found"))
        if len(package_tuple[1].whatUsed.keys()) > 0:
            HTMLwhatusedref = "what_used_" + `package_tuple[1].uniqueNumber` + ".html"
            outfile.write('<A href="' + HTMLwhatusedref + '">'+_('where used')+'</A>')
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
        outfile.write(')</DIV></TD><TD>'+idesc+'</TD><TD CLASS="whereused">')
        if len(item.whereUsed.keys()) > 0:
            HTMLwhereusedref = "where_used_" + `item.uniqueNumber` + ".html"
            outfile.write('<A href="' + HTMLwhereusedref + '">' + _('where used')+'</A> / ')
        else:
            outfile.write('- / ')
        if len(item.whatUsed.keys()) > 0:
            HTMLwhatusedref = "what_used_" + `item.uniqueNumber` + ".html"
            outfile.write('<A href="' + HTMLwhatusedref + '">' + _('what used')+'</A>')
        else:
            outfile.write('-')
        outfile.write('</TD></TR>\n')


    fileInfoList = metaInfo.fileInfoList
    html_dir = metaInfo.htmlDir
    top_level_directory = metaInfo.topLevelDirectory
    if metaInfo.useCache: cache = hypercache.cache(metaInfo.cacheDirectory)
    pbarInit(_("Creating hyperlinked source file pages"),0,len(fileInfoList))

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

    k = 0
    for file_info in fileInfoList:
        # update progressbar
        k += 1
        pbarUpdate(k)

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

        # read up the source file
        infile = fopen(file_info.fileName, "r", metaInfo.encoding)
        infile_line_list = infile.readlines()
        infile.close()

        # generate a file name for us to write to (+1 for delimiter)
        outfilename = os.path.split(file_info.fileName)[1].replace(".", "_")
        outfilename += "_" + `file_info.uniqueNumber` + ".html"

        outfile = fopen(html_dir + outfilename, "w", metaInfo.encoding)
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
            if metaInfo.useCache:
                if cache.check(file_info.fileName,'code'):
                    code = cache.get(file_info.fileName,'code')
                else:
                    code = hypercode(infile_line_list, sqlkeywords, sqltypes)
                    cache.put(file_info.fileName, 'code', code)
            else:
                code = hypercode(infile_line_list, sqlkeywords, sqltypes)
            # Shall we hyperlink calls?
            if metaInfo.linkCodeCalls:
                if len(file_info.packageInfoList) > 0:
                    for p in range(len(file_info.packageInfoList)):
                        for w in file_info.packageInfoList[p].whatUsed.keys():
                            for u in file_info.packageInfoList[p].whatUsed[w]:
                                if u[2] in ['file','pkg','view']: continue
                                try: opname = u[3].parent.name
                                except: opname = ''
                                oname = u[3].name
                                href  = os.path.split(u[0].fileName)[1].replace('.','_') \
                                  + '_' + `u[0].uniqueNumber` + '.html#' + `u[1]`
                                patt = re.compile('\\b('+opname+')\\.('+oname+')\\b',re.I)
                                oricode = code
                                code = patt.sub('\\1.<A HREF="'+href+'">\\2</A>',code)
                                if code==oricode and file_info.fileName==u[0].fileName: # no match on full name
                                    patt = re.compile('\\b('+oname+')(\\s*\\()')
                                    code = patt.sub('<A HREF="'+href+'">\\1</A>\\2',code)
            outfile.write( code )
            outfile.write("</pre></code>\n")
            outfile.write('<DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV><BR>\n')
            outfile.write(MakeHTMLFooter(file_info.fileName[len(top_level_directory)+1:]))

        outfile.close()

    # complete line on task completion
    pbarClose()


def CreateIndexPage():
    """Generates the main index page"""
    printProgress(_("Creating site index page"))

    html_dir = metaInfo.htmlDir
    script_name = metaInfo.scriptName

    outfile = fopen(html_dir + 'index.html', "w", metaInfo.encoding)
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

    def makeUsageTableHead(otype, oname, page):
        """
        Create the table header for usage tables
        @param string otype object type
        @param string oname name of the used object
        @param string page 'where' or 'what' (used)
        @return string html header
        """
        tname = otype+' '+oname
        if page=='where':
            html  = "<H1>" + _('Where Used List for %s') % tname +"</H1>\n"
        else:
            html  = "<H1>" + _('What Used List for %s') % tname +"</H1>\n"
        html += "<TABLE CLASS='apilist'>\n"
        html += "  <TR><TH>"+_('Object')+"</TH><TH>"+_('File')+"</TH><TH>"+_('Line')+"</TH></TR>\n"
        return html

    def makeUsageColumn(filename,utuple,trclass=''):
        """
        Create the usage table
        @param string filename name of the file the usage was found in
        @param tuple utuple usage tuple
        @return string html usage table
        """
        if trclass!='': trclass = ' CLASS="'+trclass+'"'
        filename_short = filename[len(top_level_directory)+1:]
        line_number = utuple[1]
        unique_number = utuple[0].uniqueNumber
        html_file = os.path.split(filename)[1].replace(".", "_") + "_" + `unique_number` + ".html"
        utype = utuple[2]
        uObj = utuple[3]
        if utype in ['func','proc']: uname = uObj.parent.name + '.'
        else: uname = ''
        if utype=='file': uname = filename[len(top_level_directory)+1:]
        elif uObj.javadoc.isDefault(): uname += uObj.name.lower()
        else: uname += uObj.javadoc.name
        if utype in ['func','proc']: uname += '()'
        if utype=='func'  : utype = 'function'
        elif utype=='proc': utype = 'procedure'
        elif utype=='pkg' : utype = 'package'

        html = '  <TR'+trclass+'><TD>' + utype + ' '

        # only make hypertext references for SQL files for now
        if utuple[0].fileType == "sql":
            if not metaInfo.useJavaDoc or uObj.javadoc.isDefault():
                html += uname + '</TD><TD>'
            else:
                html += '<A HREF="' + html_file + '#' + uObj.javadoc.name + '_' + `uObj.uniqueNumber` + '">' + uname + '</A></TD><TD>'
            if metaInfo.includeSource:
                html += '<A HREF="' + html_file + '">' + filename_short + '</A></TD><TD ALIGN="right">'
                html += '<A href="' + html_file + '#' + `line_number` + '">' + `line_number` + '</A>'
        else:
            html += uname + '</TD><TD>' + filename_short + '</TD><TD ALIGN="right">' + `line_number`

        html += '</TD></TR>\n'
        return html

    def makeUsagePage(fname,page,otype,obj):
        """
        Write the where/what used page
        @param string fname file name w/ path
        @param string page 'where' or 'what'
        @param string otype object type ('view','pkg','func','proc')
        @param object obj object info (object of type ElemInfo, see hypercore.py)
        """
        if page=='where':
            used_keys = obj.whereUsed.keys()
            used_list = obj.whereUsed
            pname = _("Where Used List for %s") % obj.name
        else:
            used_keys = obj.whatUsed.keys()
            used_list = obj.whatUsed
            pname = _("What Used List for %s") % obj.name
        outfile = fopen(fname, 'w', metaInfo.encoding)
        if otype=='view':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('view'),obj.name,page) )
        elif otype=='pkg':
            outfile.write(MakeHTMLHeader(obj.name + ' ' + pname))
            outfile.write( makeUsageTableHead(_('package'),obj.name,page) )
        elif otype=='func':
            outfile.write(MakeHTMLHeader(obj.name.lower() + ' '+_('from Package')+' ' + obj.parent.name))
            outfile.write( makeUsageTableHead(_('function'),obj.name.lower() + " <I>"+_('from package')+" " + obj.parent.name + " </I>", page) )
        elif otype=='proc':
            outfile.write(MakeHTMLHeader(obj.name.lower() + ' '+_('from Package')+' ' + obj.parent.name))
            outfile.write( makeUsageTableHead(_('procedure'),obj.name.lower() + " <I>"+_('from package')+" " + obj.parent.name + " </I>", page) )
        else:
            logger.warn(_('makeUsagePage called for undefined type "%s"'),otype)
        used_keys.sort(CaseInsensitiveComparison)
        k = 0;
        for key in used_keys:
            for usedtuple in used_list[key]:
                outfile.write( makeUsageColumn(key,usedtuple,'tr'+`k % 2`) )
                k += 1
        outfile.write("</TABLE>")
        outfile.write(MakeHTMLFooter(pname))
        outfile.close()


    html_dir = metaInfo.htmlDir
    fileInfoList = metaInfo.fileInfoList
    pbarInit(_("Creating 'where used' pages"),0,len(fileInfoList))

    # loop through files
    i = 0
    for file_info in fileInfoList:

        # Update progressbar
        i += 1
        pbarUpdate(i)

        # skip all non-sql files
        if file_info.fileType != "sql":
            continue

        # loop through views
        for view_info in file_info.viewInfoList:
            #create a "where used" file
            if len(view_info.whereUsed.keys()) != 0:
                whereusedfilename = html_dir + "where_used_" + `view_info.uniqueNumber` + ".html"
                makeUsagePage(whereusedfilename,'where','view',view_info)
            #create a "what used" file
            if len(view_info.whatUsed.keys()) != 0:
                whatusedfilename = html_dir + "what_used_" + `view_info.uniqueNumber` + ".html"
                makeUsagePage(whatusedfilename,'what','view',view_info)


        for package_info in file_info.packageInfoList:
            #create a "where used" file
            if len(package_info.whereUsed.keys()) != 0:
                whereusedfilename = html_dir + "where_used_" + `package_info.uniqueNumber` + ".html"
                makeUsagePage(whereusedfilename,'where','pkg',package_info)
            #create a "what used" file
            if len(package_info.whatUsed.keys()) != 0:
                whatusedfilename = html_dir + "what_used_" + `package_info.uniqueNumber` + ".html"
                makeUsagePage(whatusedfilename,'what','pkg',package_info)

            #look for any of this packages' functions
            for function_info in package_info.functionInfoList:
                #create a "where used" file
                if len(function_info.whereUsed.keys()) != 0:
                    whereusedfilename = html_dir + "where_used_" + `function_info.uniqueNumber` + ".html"
                    makeUsagePage(whereusedfilename,'where','func',function_info)
                #create a "what used" file
                if len(function_info.whatUsed.keys()) != 0:
                    whatusedfilename = html_dir + "what_used_" + `function_info.uniqueNumber` + ".html"
                    makeUsagePage(whatusedfilename,'what','func',function_info)

            #look for any of this packages procedures
            for procedure_info in package_info.procedureInfoList:
                #create a "where used" file
                if len(procedure_info.whereUsed.keys()) != 0:
                    whereusedfilename = html_dir + "where_used_" + `procedure_info.uniqueNumber` + ".html"
                    makeUsagePage(whereusedfilename,'where','proc',procedure_info)
                #create a "what used" file
                if len(procedure_info.whatUsed.keys()) != 0:
                    whatusedfilename = html_dir + "what_used_" + `procedure_info.uniqueNumber` + ".html"
                    makeUsagePage(whatusedfilename,'what','proc',procedure_info)

    # complete line on task completion
    pbarClose()


def CreateDepGraphIndex():
    """ Generate the depgraphs and their index page """

    if metaInfo.indexPage['depgraph']=='':
        return

    g = depgraph(metaInfo.graphvizMod, metaInfo.encoding, metaInfo.depGraphDelTmp)
    if not g.deps_ok: # we cannot do anything
        logger.error(_('Graphviz trouble - unable to generate the graph'))
        return

    i = 0
    pbarInit(_('Creating dependency graphs'), i, metaInfo.depGraphCount)

    g.set_fontname(metaInfo.fontName)
    g.set_fontsize(metaInfo.fontSize)
    g.set_ranksep(metaInfo.graphRankSepDot,'dot')
    g.set_ranksep(metaInfo.graphRankSepTwopi,'twopi')
    g.set_ranksep(metaInfo.graphLenFdp,'fdp')
    g.set_ranksep(metaInfo.graphLenNeato,'neato')
    g.set_ranksep(metaInfo.graphDistCirco,'circo')

    if metaInfo.useCache: cache = hypercache.cache(metaInfo.cacheDirectory)

    def makePng(gtyp,i):
        """
        Create the graph file
        @param string gtyp which depGraph to process (file2file, file2object...)
        """
        if metaInfo.makeDepGraph[gtyp]:
            if metaInfo.depGraph[gtyp]:
                gname = 'depgraph_'+gtyp+'.png'
                # check the cache first
                done = False
                if metaInfo.useCache:
                    tmp = cache.get(gtyp,'depdata').split('\n')
                    if tmp==metaInfo.depGraph[gtyp]:
                        copy2(os.path.join(metaInfo.cacheDirectory,gname), os.path.join(metaInfo.htmlDir,gname))
                        done = True
                if not done:
                    g.set_graph(metaInfo.depGraph[gtyp])
                    res = g.make_graph(metaInfo.htmlDir + gname)
                    if res=='':
                        if metaInfo.useCache:
                            cache.put(gtyp,'depdata','\n'.join(metaInfo.depGraph[gtyp]))
                            copy2(os.path.join(metaInfo.htmlDir,gname), os.path.join(metaInfo.cacheDirectory,gname))
                    else:
                        logger.error(_('Graphviz threw an error:') + res.strip())
            else: # no data, no graph
                if gtyp=='file2file': name = _('file to file')
                elif gtyp=='file2object': name = _('file to object')
                elif gtyp=='object2file': name = _('object to file')
                elif gtyp=='object2object': name = _('object to object')
                else: name = _('unknown dependency graph type')
                logger.debug(_('No dependency data for %s'), name)
            i += 1
            pbarUpdate(i)
        return i
                
    # draw the graphs
    i = makePng('file2file',i)
    i = makePng('file2object',i)
    i = makePng('object2file',i)
    i = makePng('object2object',i)

    outfile = fopen(metaInfo.htmlDir + metaInfo.indexPage['depgraph'], "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader('depgraph'))
    outfile.write("<H1>"+_('Dependency Graph')+"</H1>\n")

    sel = _('Access from') + " <SELECT NAME=\"graph\" onChange=\"document.getElementById('depimg').src='depgraph_'+this.value+'.png';\">"
    if metaInfo.makeDepGraph['file2file']:
        sel += "<OPTION VALUE='file2file'>" + _("file to file") + "</OPTION>"
    if metaInfo.makeDepGraph['file2object']:
        sel += "<OPTION VALUE='file2object'>" + _("file to object") + "</OPTION>"
    if metaInfo.makeDepGraph['object2file']:
        sel += "<OPTION VALUE='object2file'>" + _("object to file") + "</OPTION>"
    if metaInfo.makeDepGraph['object2object']:
        sel += "<OPTION VALUE='object2object'>" + _("object to object") + "</OPTION>"
    sel += "</SELECT><BR>"

    for obj in ['file2file','file2object','object2file','object2object']:
        if metaInfo.makeDepGraph[obj]:
            defsrc = 'depgraph_' + obj
            break;

    outfile.write('<DIV ALIGN="center">\n' + sel + '\n<IMG ID="depimg" SRC="'+ defsrc + '.png" ALT="'+_('Dependency Graph')+'" ALIGN="center">\n</DIV>\n')

    outfile.write(MakeHTMLFooter('depgraph'))
    outfile.close()

    pbarClose()

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
    metaInfo.encoding      = config.get('General','encoding','utf8')
    gettext.bind_textdomain_codeset('hypersql',metaInfo.encoding.upper())
    #gettext.bind_textdomain_codeset('hyperjdoc',metaInfo.encoding.upper())
    setJDocEncoding(metaInfo.encoding.upper())
    metaInfo.projectInfo   = unicode(config.get('General','project_info',''),metaInfo.encoding)
    infofile               = config.get('General','project_logo_url','')
    if infofile == '':
      metaInfo.projectLogo = config.get('General','project_logo','')
    else:
      metaInfo.projectLogo = infofile
    infofile               = config.get('General','project_info_file','')
    if infofile != '' and os.path.exists(infofile):
        infile = fopen(infofile, "r", metaInfo.encoding)
        fileLines = ''.join(infile.readlines())
        infile.close()
        metaInfo.projectInfo += fileLines
    JavaDocVars['ticket_url']   = config.get('General','ticket_url','')
    JavaDocVars['wiki_url']     = config.get('General','wiki_url','')
    # Section FILENAMES
    metaInfo.topLevelDirectory  = config.get('FileNames','top_level_directory','.') # directory under which all files will be scanned
    JavaDocVars['top_level_dir_len'] = len(metaInfo.topLevelDirectory)
    metaInfo.rcsnames           = config.getList('FileNames','rcsnames',['RCS','CVS','.svn']) # directories to ignore
    metaInfo.sql_file_exts      = config.getList('FileNames','sql_file_exts',['sql', 'pkg', 'pkb', 'pks', 'pls']) # Extensions for files to treat as SQL
    metaInfo.cpp_file_exts      = config.getList('FileNames','cpp_file_exts',['c', 'cpp', 'h']) # Extensions for files to treat as C
    if len(sys.argv)>1: defCacheDir = os.path.split(sys.argv[0])[0] + os.sep + "cache" + os.sep + sys.argv[1] + os.sep
    else: defCacheDir = os.path.split(sys.argv[0])[0] + os.sep + "cache" + os.sep
    metaInfo.cacheDirectory     = config.get('FileNames','cache_dir',defCacheDir)
    metaInfo.useCache           = config.getBool('Process','cache',True)
    metaInfo.htmlDir            = config.get('FileNames','htmlDir',os.path.split(sys.argv[0])[0] + os.sep + "html" + os.sep)
    metaInfo.css_file           = config.get('FileNames','css_file','hypersql.css')
    metaInfo.css_url            = config.get('FileNames','css_url','')
    metaInfo.indexPage          = {}
    metaInfo.indexPageCount     = 1 # We at least have the main index page
    metaInfo.indexPageName      = {}
    confPage('filepath','FileNameIndexWithPathnames.html',_('File Names by Path Index'),True)
    confPage('file','FileNameIndexNoPathnames.html',_('File Name Index'),True)
    confPage('view','ViewIndex.html',_('View Index'),False)
    confPage('package','PackageIndex.html',_('Package Index'),True)
    confPage('package_full','PackagesWithFuncsAndProcsIndex.html',_('Full Package Listing'),True)
    confPage('function','FunctionIndex.html',_('Function Index'),True)
    confPage('procedure','ProcedureIndex.html',_('Procedure Index'),True)
    confPage('bug','BugIndex.html',_('Bug List'),True)
    confPage('todo','TodoIndex.html',_('Todo List'),True)
    confPage('report','ReportIndex.html',_('Verification Report'),True)
    confPage('stat','StatIndex.html',_('Code Statistics'),True)
    confPage('depgraph','DepGraphIndex.html',_('Dependency Graphs'),True)
    # Sections PAGES and PAGENAMES are handled indirectly via confPage() in section FileNames
    # Section PROCESS
    metaInfo.blindOffset = abs(config.getInt('Process','blind_offset',0)) # we need a positive integer
    metaInfo.includeSource = config.getBool('Process','include_source',True)
    metaInfo.useJavaDoc = config.getBool('Process','javadoc',True)
    metaInfo.linkCodeCalls = config.getBool('Process','link_code_calls',True)
    # Section VERIFICATION
    JavaDocVars['javadoc_mandatory'] = config.getBool('Verification','javadoc_mandatory',False)
    JavaDocVars['verification'] = config.getBool('Verification','verify_javadoc',False)
    JavaDocVars['mandatory_tags'] = config.getList('Verification','mandatory_tags',[])
    # Section DEPGRAPH
    metaInfo.graphvizMod   = config.get('DepGraph','processor','fdp')
    metaInfo.fontName      = config.get('DepGraph','fontname','')
    metaInfo.fontSize      = config.get('DepGraph','fontsize','')
    metaInfo.graphRankSepDot  = config.get('DepGraph','ranksep_dot','')
    metaInfo.graphRankSepTwopi  = config.get('DepGraph','ranksep_twopi','')
    metaInfo.graphLenNeato = config.get('DepGraph','len_neato','')
    metaInfo.graphLenFdp = config.get('DepGraph','len_fdp','')
    metaInfo.graphDistCirco = config.get('DepGraph','mindist_circo','')
    metaInfo.depGraphObjects = config.getList('DepGraph','objects',['view','pkg','proc','func'])
    metaInfo.makeDepGraph = {}
    metaInfo.makeDepGraph['file2file']     = config.getBool('DepGraph','file2file',True)
    metaInfo.makeDepGraph['file2object']   = config.getBool('DepGraph','file2object',False)
    metaInfo.makeDepGraph['object2file']   = config.getBool('DepGraph','object2file',True)
    metaInfo.makeDepGraph['object2object'] = config.getBool('DepGraph','object2object',True)
    metaInfo.depGraphCount = 0
    if metaInfo.makeDepGraph['file2file']:     metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['file2object']:   metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['object2file']:   metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['object2object']: metaInfo.depGraphCount += 1
    metaInfo.depGraphDelTmp = config.getBool('DepGraph','deltmp',True)

def confDeps():
    """ Check dependent options and fix them, if necessary """
    if metaInfo.indexPage['depgraph']!='':
        dg = depgraph()
        if not dg.deps_ok: metaInfo.indexPage['depgraph'] = ''

def confLogger():
    """ Setup logging """
    logging.addLevelName(99,'NONE')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler( config.get('Logging','logfile'), 'a', metaInfo.encoding )
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

def pbarInit(prefix,start,end):
    """
    Initialize ProgressBar
    @param string prefix the progress message to pass
    @param int start start value (usually 0)
    @param int end max value
    """
    logger.debug(prefix)
    if config.getBool('Logging','progress',True):
        pbar.__init__(prefix,start,end)
        pbar.draw()

def pbarUpdate(newVal):
    """
    Update the ProgressBar
    @param int newVal new value (current state)
    """
    if config.getBool('Logging','progress',True):
        pbar.update(newVal)

def pbarClose():
    """ At end of processing, we need a newline """
    if config.getBool('Logging','progress',True): print


if __name__ == "__main__":

    # Read configuration
    pbar = progressBar() # make it global
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
      print _('No config file found, using defaults.')

    metaInfo = MetaInfo() # This holds top-level meta information, i.e., lists of filenames, etc.
    metaInfo.versionString = "2.8"
    metaInfo.scriptName = sys.argv[0]
    configRead()
    confDeps()

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
    CreateDepGraphIndex()
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
