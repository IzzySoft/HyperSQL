"""
Scan for (PL/)SQL objects
"""
__revision__ = '$Id$'

from iz_tools.system import fopen
from hypercore.helpers  import eatStrings, getWordLineNr
from hypercore.elements import *
from hypercore.javadoc  import *
import hypercore.cache
import re, gettext, locale, os
from hypercore.logger import logg
logname = 'ParseSQL'
logger = logg.getLogger(logname)
from progress import *

# Setup gettext support
gettext.bindtextdomain('hypersql', langpath)
gettext.textdomain('hypersql')
lang = gettext.translation('hypersql', langpath, languages=langs, fallback=True)
_ = lang.ugettext

try:
    from hypercore.xml_forms import OraForm
except:
    pass


#============================================================[ Object Scan ]===
#------------------------------------------------------------------------------
def ElemInfoAppendJdoc(oInfo,oType,lineNumber,jdoc):
    """
    Append Javadoc info if object matches
    @param object oInfo ElemInfo object
    @param string oType object type checked for lineNumber
    @param int lineNumber number of the currently processed line
    @param object jdoc JavaDoc object
    """
    oInfo.lineNumber = lineNumber
    for j in range(len(jdoc)):
        ln = jdoc[j].lineNumber - lineNumber
        if ( oInfo.name.lower()==jdoc[j].name.lower() and jdoc[j].objectType==oType) or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
            oInfo.javadoc = jdoc[j]
            if hasattr(oInfo,'bugs'):
                if len(jdoc[j].bug) > 0 and metaInfo.indexPage['bug'] != '':
                    for ib in range(len(jdoc[j].bug)):
                        oInfo.bugs.addItem(jdoc[j].name,jdoc[j].bug[ib])
                if len(jdoc[j].todo) > 0 and metaInfo.indexPage['todo'] != '':
                    for ib in range(len(jdoc[j].todo)):
                        oInfo.todo.addItem(jdoc[j].name,jdoc[j].todo[ib])

    if not oInfo.javadoc.ignore:
        mname = oInfo.javadoc.name or oInfo.name
        mands = oInfo.javadoc.verify_mandatory()
        for mand in mands:
            oInfo.verification.addItem(mname,mand)
        if JavaDocVars['javadoc_mandatory'] and oInfo.javadoc.isDefault():
            logger.warn(_('%(otype)s %(name)s has no JavaDoc information attached'), {'otype':_(oType.capitalize()),'name':oInfo.name})
            oInfo.verification.addItem(oInfo.name,'No JavaDoc information available')


#------------------------------------------------------------------------------
def FormInfoAppendJavadoc(oInfo,oType,jdoc):
    """
    Append javadoc to form elements
    @param object oInfo the form element
    @param string oType type of the element (form, pkg, func, proc)
    @param list jdoc JavaDoc object
    """
    for j in range(len(jdoc)):
      ln = jdoc[j].lineNumber - oInfo.lineNumber
      if (oInfo.name.lower()==jdoc[j].name.lower() and jdoc[j].objectType==oType) or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
        oInfo.javadoc = jdoc[j]

    if JavaDocVars['verify_forms'] and not oInfo.javadoc.ignore:
      mname = oInfo.javadoc.name or oInfo.name
      mands = oInfo.javadoc.verify_mandatory()
      oInfo.verification = PackageTaskList(oInfo.name.lower())
      for mand in mands:
          oInfo.verification.addItem(mname,mand)
      if JavaDocVars['javadoc_mandatory'] and oInfo.javadoc.isDefault():
          logger.warn(_('%(otype)s %(name)s has no JavaDoc information attached'), {'otype':_(oType.capitalize()),'name':oInfo.name})
          oInfo.verification.addItem(oInfo.name,'No JavaDoc information available')


#------------------------------------------------------------------------------
def fixQuotedName(name):
    """
    Remove possible double-quotes around and trailing opening parenthesis from object names
    @param string name name string to check
    @return string name fixed name
    """
    if len(name)<3: return name
    if name[0]=='"' and name[len(name)-1]=='"': name = name[1:len(name)-1]
    if name[len(name)-1]=='(': return name[0:len(name)-1]
    return name


#------------------------------------------------------------------------------
def appendGlobalTasks(otype,master,jd,uid=0,jdverify=None):
    """
    Append items from object bug/todo to their parents master list
    @param string otype    type of the object processed ('func','proc','pkg','formpkg','formpkgfunc','formpkgproc')
    @param object master   the FormInfo/PackageInfo element
    @param list   jd       the local javadoc element list
    @param object jdverify optional ElemInfo to update the javadoc verification report for. Needed for Oracle Forms
    """
    if otype not in ['func','proc','pkg','formpkg','formpkgfunc','formpkgproc']:
        logger.warn(_('Invalid object type "%(otype)s" passed to appendGlobalTasks for %(jotype)s %(name)s'), {'otype':otype, 'jotype':jd.objectType, 'name':jd.name or '[unknown]'})
        return
    if len(jd.bug)>0 and metaInfo.indexPage['bug'] != '':
        for ib in range(len(jd.bug)):
            if otype in ['pkg','formpkg']:        master.bugs.addItem(jd.name,jd.bug[ib],jd.author,master.uniqueNumber)
            elif otype in ['func','formpkgfunc']: master.bugs.addFunc(jd.name,jd.bug[ib],jd.author,master.uniqueNumber)
            elif otype in ['proc','formpkgproc']: master.bugs.addProc(jd.name,jd.bug[ib],jd.author,master.uniqueNumber)
    if len(jd.todo)>0 and metaInfo.indexPage['todo'] != '':
        for ib in range(len(jd.todo)):
            if otype in ['pkg','formpkg']:        master.todo.addItem(jd.name,jd.todo[ib],jd.author,master.uniqueNumber)
            elif otype in ['func','formpkgfunc']: master.todo.addFunc(jd.name,jd.todo[ib],jd.author,master.uniqueNumber)
            elif otype in ['proc','formpkgproc']: master.todo.addProc(jd.name,jd.todo[ib],jd.author,master.uniqueNumber)
    if jdverify and not jdverify.javadoc.ignore and metaInfo.indexPage['report'] !='':
        if otype in ['pkg','formpkg'] and jdverify.verification.allItemCount()>0:
          for ver in jdverify.verification.items:
            master.verification.addItem(ver.name,ver.desc,ver.author,ver.uid)
        elif otype in ['formpkgfunc','formpkgproc']:
            mname = jdverify.javadoc.name or jdverify.name
            mands = jdverify.javadoc.verify_mandatory()
            for mand in mands:
                if otype == 'formpkgfunc':   master.verification.addFunc(mname,mand,jdverify.javadoc.author,jdverify.uniqueNumber)
                elif otype == 'formpkgproc': master.verification.addProc(mname,mand,jdverify.javadoc.author,jdverify.uniqueNumber)
            if JavaDocVars['javadoc_mandatory'] and jdverify.javadoc.isDefault():
                logger.warn(_('%(otype)s %(name)s has no JavaDoc information attached'), {'otype':_(otype.capitalize()),'name':jdverify.name})
                master.verification.addFunc(jdverify.name,'No JavaDoc information available')
        #elif otype == 'proc'      : master.verification.addProc(jd.name,ver,jd.author,master.uniqueNumber)


#------------------------------------------------------------------------------
def parseForm(file_info):
    """
    Parse an Oracle Forms XML file
    @param object file_info the FileInfo object containint the form data
    @param object config instance of HyperConf
    """
    # config.get(..)
    proc_mark = metaInfo.config.get('Forms','proc_mark','Procedure').upper()
    func_mark = metaInfo.config.get('Forms','func_mark','Function').upper()
    pcks_mark  = metaInfo.config.get('Forms','pcks_mark','Package Body').upper()
    pck_mark  = metaInfo.config.get('Forms','pck_mark','Package Body').upper()
    formcode = ''

    if metaInfo.useCache: cache = hypercore.cache.cache(metaInfo.cacheDirectory)

    form = OraForm(file_info.fileName)
    modinfo = form.getModuleInfo()
    libinfo = form.getLibraryInfo()
    form_info = FormInfo()
    form_info.parent = file_info
    form_info.stats = form.getStats()
    if modinfo:
        form_info.formType = 'module'
        form_info.title     = modinfo['title']
    elif libinfo:
        form_info.formType = 'library'
        form_info.objects  = libinfo['objects']
    else:
        form_info.formType = 'unknown'
    form_info.name = form.getModuleName()
    form_info.lineNumber = 1

    for unit in form.getUnits(): # name, type, code
        if not unit['type']: continue # deleted objects have their type removed
        linenr = formcode.count('\n') +1
        if unit['code']: formcode += unit['code'] + '\n'
        if unit['type'].upper() == proc_mark:
            elem = StandAloneElemInfo()
            elem.parent = form_info
            elem.name = unit['name']
            elem.lineNumber = linenr
            form_info.procedureInfoList.append(elem)
        elif unit['type'].upper() == func_mark:
            elem = StandAloneElemInfo()
            elem.parent = form_info
            elem.name = unit['name']
            elem.lineNumber = linenr
            form_info.functionInfoList.append(elem)
        elif unit['type'].upper() == pck_mark:
            elem = PackageInfo()
            elem.parent = form_info
            elem.name = unit['name']
            elem.lineNumber = linenr
            ###TODO: Go for more details (pkg.proc/func/...)
            # temporary: Obtain the child elements via javadoc
            for jd in ScanJavaDoc(unit['code'].split('\n'),file_info.fileName):
              if jd.objectType not in ['function','procedure']: continue
              if not jd.name: continue
              fu = ElemInfo()
              fu.name   = jd.name
              fu.parent = elem
              fu.lineNumber = jd.lineNumber
              fu.javadoc = jd
              if jd.objectType == 'function':
                elem.functionInfoList.append(fu)
              elif jd.objectType == 'procedure':
                elem.procedureInfoList.append(fu)
            form_info.packageInfoList.append(elem)
        elif unit['type'].upper() == pcks_mark:
            continue    # skip package specifications
        else:
            logger.info(_('Skipped unknown form unit type "%(type)s" in %(file)s'),{'type':unit['type'],'file':file_info.fileName})
    for trigger in form.getTrigger():
        linenr = formcode.count('\n') +1
        if trigger['code']: formcode += trigger['code']
        elem = StandAloneElemInfo()
        elem.parent = form_info
        elem.name = trigger['name']
        elem.lineNumber = linenr
        form_info.triggerInfoList.append(elem)

    form_info.codesize = len(formcode)
    file_info.formInfoList.append(form_info)
    ###TODO: Forms stats
    file_info.xmlbytes = os.path.getsize(file_info.fileName)
    file_info.xmlcodebytes = len(formcode)
    #file_info.lines = formcode.count('\n')
    if metaInfo.useCache and not cache.check(file_info.fileName,'formcode'):
        cache.put(file_info.fileName, 'formcode', formcode)
    if metaInfo.useJavaDoc:
        jdoc = ScanJavaDoc(formcode, file_info.fileName)
        FormInfoAppendJavadoc(form_info,'form',jdoc)
        for pkg in form_info.packageInfoList:
            FormInfoAppendJavadoc(pkg,'pkg',jdoc)
            ptl = StandAloneElemInfo()
            ptl.bugs = PackageTaskList(pkg.name)
            ptl.todo = PackageTaskList(pkg.name)
            ptl.verification = PackageTaskList(pkg.name)
            appendGlobalTasks('formpkg',ptl,pkg.javadoc,pkg.uniqueNumber,pkg)
            for func in pkg.functionInfoList:
                appendGlobalTasks('formpkgfunc',ptl,func.javadoc,func.uniqueNumber,func)
            for func in pkg.procedureInfoList:
                appendGlobalTasks('formpkgproc',ptl,func.javadoc,func.uniqueNumber,func)
            form_info.bugs.pkgs.append(ptl.bugs)
            form_info.todo.pkgs.append(ptl.todo)
            form_info.verification.pkgs.append(ptl.verification)
        for func in form_info.functionInfoList:
            FormInfoAppendJavadoc(func,'function',jdoc)
            appendGlobalTasks('func',form_info,func.javadoc,func.uniqueNumber)
        for proc in form_info.procedureInfoList:
            FormInfoAppendJavadoc(proc,'procedure',jdoc)
            appendGlobalTasks('func',form_info,proc.javadoc,proc.uniqueNumber)


#------------------------------------------------------------------------------
def ScanFilesForObjects():
    """
    Scans files from metaInfo.fileInfoList for views and packages and collects
    some metadata about them (name, file, lineno). When encountering a package
    spec, it also scans for its functions and procedures.
    It simply searches the source file for keywords. With each object info,
    file name and line number are stored (and can be used to identify parent
    and children) - for functions and procedures contained in packages, a link
    to their parent is stored along.
    """
    pbarInit(_("Scanning source files for views and packages"),0,len(metaInfo.fileInfoList), logname)

    if metaInfo.indexPage['form'] and not OraForm:
        logger.error(_('Cannot process Oracle Forms XML files - SAX API (pyxml) seems to be unavailable.'))

    i = 0

    # first, find views in files
    dot_count = 1
    for file_info in metaInfo.fileInfoList:

        # print progress
        i += 1
        pbarUpdate(i)

        # skip all non-sql files
        if file_info.fileType not in ['sql','xml']:
            continue

        # Oracle Forms XML files have special processing:
        if file_info.fileType in ['xml'] and metaInfo.indexPage['form'] !='':
            parseForm(file_info)
            continue

        #### All other files (except for Oracle Forms XML) are processed here:
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
        pks_count = -1
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
                fileLines[lineNumber+1], matched_string = eatStrings(fileLines[lineNumber+1])
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

            for token_index in range(len(token_list)):
                # find types
                if metaInfo.indexPage['type']:
                    # look for CREATE [OR REPLACE] TRIGGER [schema.]trigger (...), making sure enough tokens exist
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "TYPE" \
                    and token_list[token_index].upper() in ['CREATE','REPLACE']:
                        tab_info = StandAloneElemInfo()
                        tab_info.parent = file_info
                        if len(token_list) > token_index+2:
                          tab_info.name = token_list[token_index+2]
                        else:
                          tab_info.name = token_list1[0]
                        tab_info.name = fixQuotedName(tab_info.name)
                        ElemInfoAppendJdoc(tab_info,'type',lineNumber+1,jdoc)
                        file_info.typeInfoList.append(tab_info)
                        continue

                # find trigger.
                if metaInfo.indexPage['trigger']:
                    # look for CREATE [OR REPLACE] TRIGGER [schema.]trigger (...), making sure enough tokens exist
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "TRIGGER" \
                    and token_list[token_index].upper() in ['CREATE','REPLACE']:
                        tab_info = StandAloneElemInfo()
                        tab_info.parent = file_info
                        if len(token_list) > token_index+2:
                          tab_info.name = token_list[token_index+2]
                        else:
                          tab_info.name = token_list1[0]
                        tab_info.name = fixQuotedName(tab_info.name)
                        ElemInfoAppendJdoc(tab_info,'trigger',lineNumber+1,jdoc)
                        file_info.triggerInfoList.append(tab_info)
                        continue

                # find tables.
                if metaInfo.indexPage['tab']:
                    # look for CREATE [GLOBAL TEMPORARY] TABLE [schema.]table (...), making sure enough tokens exist
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "TABLE" \
                    and token_list[token_index].upper() in ['CREATE','TEMPORARY']:
                        tab_info = StandAloneElemInfo()
                        tab_info.parent = file_info
                        if len(token_list) > token_index+2:
                          tab_info.name = token_list[token_index+2]
                        else:
                          tab_info.name = token_list1[0]
                        tab_info.name = fixQuotedName(tab_info.name)
                        ElemInfoAppendJdoc(tab_info,'table',lineNumber+1,jdoc)
                        file_info.tabInfoList.append(tab_info)
                        continue

                # find views
                if metaInfo.indexPage['view']:
                    # look for CREATE VIEW, REPLACE VIEW, FORCE VIEW, making sure enough tokens exist
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "VIEW" \
                    and token_list[token_index].upper() in ['CREATE','REPLACE','FORCE','EDITIONABLE']:
                        view_info = StandAloneElemInfo()
                        view_info.parent = file_info
                        if len(token_list) > token_index+2:
                          view_info.name = token_list[token_index+2]
                        else:
                          view_info.name = token_list1[0]
                        view_info.name = fixQuotedName(view_info.name)
                        ElemInfoAppendJdoc(view_info,'view',lineNumber+1,jdoc)
                        file_info.viewInfoList.append(view_info)
                        continue

                # find mviews.
                if metaInfo.indexPage['mview']:
                    # CREATE MATERIALIZED VIEW [schema.]mview ...
                    if len(token_list) > token_index+2 \
                    and token_list[token_index+2].upper() == "VIEW" \
                    and token_list[token_index+1].upper() == "MATERIALIZED" \
                    and token_list[token_index].upper() == "CREATE":
                        view_info = StandAloneElemInfo()
                        view_info.parent = file_info
                        if len(token_list) > token_index+3:
                          view_info.name = token_list[token_index+3]
                        else:
                          view_info.name = token_list1[0]
                        view_info.name = fixQuotedName(view_info.name)
                        ElemInfoAppendJdoc(view_info,'mview',lineNumber+1,jdoc)
                        file_info.mviewInfoList.append(view_info)
                        continue

                # find synonym definitions
                if metaInfo.indexPage['synonym']:
                    # CREATE [OR REPLACE] [PUBLIC] SYNONYM [schema.]synonym FOR [schema.]object [@dblink]
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "SYNONYM" \
                    and token_list[token_index].upper() in ['CREATE','REPLACE','PUBLIC'] \
                    and not (token_list[token_index-1].upper()=="DROP" or (token_index>1 and token_list[token_index-2].upper()=="DROP")):
                        syn_info = StandAloneElemInfo()
                        syn_info.parent = file_info
                        if len(token_list) > token_index+2:
                            syn_info.name = token_list[token_index+2]
                        else:
                            syn_info.name = token_list1[0]
                        syn_info.name = fixQuotedName(syn_info.name)
                        ElemInfoAppendJdoc(syn_info,'synonym',lineNumber+1,jdoc)
                        file_info.synInfoList.append(syn_info)
                        continue

                # find sequence definitions
                if metaInfo.indexPage['sequence']:
                    # CREATE SEQUENCE [schema.]sequence_name option(s)
                    if len(token_list) > token_index+1 \
                    and token_list[token_index+1].upper() == "SEQUENCE" \
                    and (token_list[token_index].upper() == "CREATE"):
                        seq_info = StandAloneElemInfo()
                        seq_info.parent = file_info
                        if len(token_list) > token_index+2:
                            seq_info.name = token_list[token_index+2]
                        else:
                            seq_info.name = token_list1[0]
                        seq_info.name = fixQuotedName(seq_info.name)
                        ElemInfoAppendJdoc(seq_info,'sequence',lineNumber+1,jdoc)
                        file_info.seqInfoList.append(seq_info)
                        continue

            # find package definitions - set flag if found
            # look for CREATE [OR REPLACE] PACKAGE BODY x, making sure enough tokens exist
            for token_index in range(len(token_list)):
                if len(token_list) > token_index+3 \
                   and token_list[token_index].upper() in ['CREATE','REPLACE','FORCE'] \
                       and token_list[token_index+1].upper() == "PACKAGE":
                    if token_list[token_index+2].upper() == "BODY":
                      package_info = PackageInfo()
                      package_info.uniqueNumber = metaInfo.NextIndex()
                      package_info.parent = file_info
                      package_info.name = fixQuotedName(token_list[token_index+3])
                      package_info.lineNumber = lineNumber+1
                      for j in range(len(jdoc)):
                        ln = jdoc[j].lineNumber - lineNumber
                        if (package_info.name.lower()==jdoc[j].name.lower() and jdoc[j].objectType=='pkg') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                          package_info.javadoc = jdoc[j]
                      if not package_info.javadoc.ignore: # ignore items with @ignore tag
                          pi = package_info
                          jd = pi.javadoc
                          appendGlobalTasks('pkg',pi,jd,pi.uniqueNumber)
                          mname = jd.name or pi.name
                          mands = jd.verify_mandatory()
                          for mand in mands:
                            pi.verification.addItem(mname,mand)
                          if JavaDocVars['javadoc_mandatory'] and package_info.javadoc.isDefault():
                            logger.warn(_('Package %s has no JavaDoc information attached'), mname)
                            pi.verification.addItem(mname,'No JavaDoc information available')
                          file_info.packageInfoList.append(pi) # permanent storage
                          package_count += 1 # use this flag below
                    else:
                        pks_count +=1

            if pks_count == -1: # ignore functions/procedures in package specifications
              # find functions
              for token_index in range(len(token_list)):
                if token_list[token_index].upper() == 'FUNCTION' \
                and (package_count != -1 or (token_index>0 and token_list[token_index-1] in ['CREATE','REPLACE'])):
                  if len(token_list)>token_index+1: function_name = token_list[token_index+1]
                  else: function_name = token_list1[0]
                  function_name = function_name.split('(')[0] # some are "name(" and some are "name ("
                  if package_count != -1: function_info = ElemInfo()
                  else: function_info = StandAloneElemInfo()
                  function_info.uniqueNumber = metaInfo.NextIndex()
                  if package_count != -1:
                    function_info.parent = file_info.packageInfoList[package_count]
                  else:
                    function_info.parent = file_info
                  function_info.name = fixQuotedName(function_name)
                  function_info.lineNumber = lineNumber+1
                  for j in range(len(jdoc)):
                    ln = jdoc[j].lineNumber - lineNumber
                    if (function_name.lower()==jdoc[j].name.lower() and jdoc[j].objectType=='function') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                      if function_info.javadoc.isDefault():
                        function_info.javadoc = jdoc[j]
                        function_info.javadoc.lndiff = abs(ln)
                      else:
                        if abs(ln) < function_info.javadoc.lndiff: # this desc is closer to the object
                          function_info.javadoc = jdoc[j]
                          function_info.javadoc.lndiff = abs(ln)
                  if not function_info.javadoc.ignore and package_count != -1: ###TODO: need alternative for standalone
                    fi = function_info
                    jd = fi.javadoc
                    appendGlobalTasks('func',file_info.packageInfoList[package_count],jd,fi.uniqueNumber)
                    mname = jd.name or fi.name
                    mands = jd.verify_mandatory()
                    for mand in mands:
                        file_info.packageInfoList[package_count].verification.addFunc(mname,mand,jd.author,fi.uniqueNumber)
                    if JavaDocVars['javadoc_mandatory'] and jd.isDefault():
                        if JavaDocVars['verification_log']: logger.warn(_('Function %(function)s in package %(package)s has no JavaDoc information attached'), {'function': mname, 'package': file_info.packageInfoList[package_count].name})
                        file_info.packageInfoList[package_count].verification.addFunc(mname,_('No JavaDoc information available'),jd.author,fi.uniqueNumber)
                    if JavaDocVars['verification']:
                        fupatt = re.compile('(?ims)function\s+'+mname+'\s*\((.*?)\)')
                        cparms = re.findall(fupatt,filetext)
                        if len(cparms)==0:
                            mands = jd.verify_params([])
                        elif len(cparms)==1:
                            cparms = cparms[0].split(',')
                            mands = jd.verify_params(cparms)
                        else:
                            if JavaDocVars['verification_log']: logger.debug(_('Multiple definitions for function %(package)s.%(function)s, parameters not verified'), {'package': file_info.packageInfoList[package_count].name, 'function': mname})
                        if len(cparms)<2:
                            for mand in mands:
                                file_info.packageInfoList[package_count].verification.addFunc(mname,mand,jd.author,function_info.uniqueNumber)
                  if package_count != -1:
                    if not function_info.javadoc.ignore: file_info.packageInfoList[package_count].functionInfoList.append(function_info)
                  else:
                    if not function_info.javadoc.ignore: file_info.functionInfoList.append(function_info)

              # find procedures
              for token_index in range(len(token_list)):
                if token_list[token_index].upper() == 'PROCEDURE' \
                and (package_count != -1 or (token_index>0 and token_list[token_index-1] in ['CREATE','REPLACE'])):
                  if len(token_list)>token_index+1: procedure_name = token_list[token_index+1]
                  else: procedure_name = token_list1[0]
                  procedure_name = procedure_name.split('(')[0] # some are "name(" and some are "name ("
                  if package_count == -1: procedure_info = StandAloneElemInfo()
                  else: procedure_info = ElemInfo()
                  procedure_info.uniqueNumber = metaInfo.NextIndex()
                  if package_count != -1:
                    procedure_info.parent = file_info.packageInfoList[package_count]
                  else:
                    procedure_info.parent = file_info
                  procedure_info.name = fixQuotedName(procedure_name)
                  procedure_info.lineNumber = lineNumber+1
                  for j in range(len(jdoc)):
                    ln = jdoc[j].lineNumber - lineNumber
                    if (procedure_name.lower()==jdoc[j].name.lower() and jdoc[j].objectType=='procedure') or (ln>0 and ln<metaInfo.blindOffset) or (ln<0 and ln>-1*metaInfo.blindOffset):
                      if procedure_info.javadoc.isDefault():
                        procedure_info.javadoc = jdoc[j]
                        procedure_info.javadoc.lndiff = abs(ln)
                      else:
                        if abs(ln) < procedure_info.javadoc.lndiff: # this desc is closer to the object
                          procedure_info.javadoc = jdoc[j]
                          procedure_info.javadoc.lndiff = abs(ln)
                  if not procedure_info.javadoc.ignore and package_count != -1: ###TODO: need alternative for standalone
                    pi = procedure_info
                    jd = pi.javadoc
                    appendGlobalTasks('proc',file_info.packageInfoList[package_count],jd,pi.uniqueNumber)
                    mname = jd.name or pi.name
                    mands = jd.verify_mandatory()
                    for mand in mands:
                        file_info.packageInfoList[package_count].verification.addProc(mname,mand,jd.author,pi.uniqueNumber)
                    if JavaDocVars['javadoc_mandatory'] and jd.isDefault():
                        if JavaDocVars['verification_log']: logger.warn(_('Procedure %(procedure)s in package %(package)s has no JavaDoc information attached'), {'procedure': mname, 'package': file_info.packageInfoList[package_count].name})
                        file_info.packageInfoList[package_count].verification.addProc(mname,_('No JavaDoc information available'),jd.author,pi.uniqueNumber)
                    if JavaDocVars['verification']:
                        fupatt = re.compile('(?ims)procedure\s+'+mname+'\s*\((.*?)\)')
                        cparms = re.findall(fupatt,filetext)
                        if len(cparms)==0:
                            mands = jd.verify_params([])
                        elif len(cparms)==1:
                            cparms = cparms[0].split(',')
                            mands = jd.verify_params(cparms)
                        else:
                            if JavaDocVars['verification_log']: logger.debug(_('Multiple definitions for function %(package)s.%(function)s, parameters not verified'), {'function': mname, 'package': file_info.packageInfoList[package_count].name})
                        if len(cparms)<200: # 2016-03-16: With its initial commit (1e0ecb5 on 2010-03-15), this was limited to "<2" parameters. Why is this relevant here?
                            for mand in mands:
                                file_info.packageInfoList[package_count].verification.addProc(mname,mand,jd.author,pi.uniqueNumber)
                  if package_count != -1:
                    if not procedure_info.javadoc.ignore: file_info.packageInfoList[package_count].procedureInfoList.append(procedure_info)
                  else:
                    if not procedure_info.javadoc.ignore: file_info.procedureInfoList.append(procedure_info)

    # complete line on task completion
    pbarClose()


#=============================================================[ Usage Scan ]===
#------------------------------------------------------------------------------
def findUsingObject(fInfo,lineNumber):
    """
    Identify the calling object - i.e. the object starting closest before the call
    @param  object  fInfo      FileInfo object of the current file
    @param  integer lineNumber line number of the actual call
    @return tuple   otuple     (str objectType, object objectInfo)
    """
    vObj = ElemInfo()
    mObj = ElemInfo()
    tObj = ElemInfo()
    pObj = ElemInfo()
    fObj = ElemInfo()
    prObj = ElemInfo() # stand-alone
    fuObj = ElemInfo() # stand-alone
    sqObj = ElemInfo()
    syObj = ElemInfo()
    trObj = ElemInfo()
    tyObj = ElemInfo()
    PObj = PackageInfo()
    foObj = FormInfo()
    for sInfo in fInfo.triggerInfoList:
        if sInfo.lineNumber < lineNumber: trObj = sInfo
        else: break;
    for sInfo in fInfo.typeInfoList:
        if sInfo.lineNumber < lineNumber: tyObj = sInfo
        else: break;
    for sInfo in fInfo.seqInfoList:
        if sInfo.lineNumber < lineNumber: sqObj = sInfo
        else: break;
    for sInfo in fInfo.synInfoList:
        if sInfo.lineNumber < lineNumber: syObj = sInfo
        else: break;
    for sInfo in fInfo.tabInfoList:
        if sInfo.lineNumber < lineNumber: tObj = sInfo
        else: break
    for sInfo in fInfo.viewInfoList:
        if sInfo.lineNumber < lineNumber: vObj = sInfo
        else: break
    for sInfo in fInfo.mviewInfoList:
        if sInfo.lineNumber < lineNumber: mObj = sInfo
        else: break
    for sInfo in fInfo.functionInfoList:
        if sInfo.lineNumber < lineNumber: fuObj = sInfo
        else: break
    for sInfo in fInfo.procedureInfoList:
        if sInfo.lineNumber < lineNumber: prObj = sInfo
        else: break
    for pInfo in fInfo.packageInfoList:
        if pInfo.lineNumber < lineNumber: PObj = pInfo
        for vInfo in pInfo.functionInfoList:
            if vInfo.lineNumber < lineNumber: fObj = vInfo
            else: break
        for vInfo in pInfo.procedureInfoList:
            if vInfo.lineNumber < lineNumber: pObj = vInfo
            else: break
    for sInfo in fInfo.formInfoList:
        if sInfo.lineNumber < lineNumber: foObj = sInfo
    sobj = [
            ['sequence',sqObj.lineNumber,sqObj],
            ['synonym',syObj.lineNumber,syObj],
            ['tab',tObj.lineNumber,tObj],
            ['view',vObj.lineNumber,vObj],
            ['mview',mObj.lineNumber,mObj],
            ['pkg',PObj.lineNumber,PObj],
            ['func',fObj.lineNumber,fObj],
            ['trigger',trObj.lineNumber,trObj],
            ['type',tyObj.lineNumber,tyObj],
            ['proc',pObj.lineNumber,pObj],
            ['func',fuObj.lineNumber,fuObj],
            ['proc',prObj.lineNumber,prObj],
            ['form',foObj.lineNumber,foObj]
           ]
    sobj.sort(key=lambda obj: obj[1], reverse=True)
    if sobj[0][1] < 0: rtype = 'file' # No object found
    else: rtype = sobj[0][0]
    return rtype,sobj[0][2]


#------------------------------------------------------------------------------
def addWhereUsed(objectInfo,fileInfo,lineNumber,otype):
    """
    Add where_used and what_used info to an object (view, procedure, function, ...)
    @param object objectInfo the view_info/function_info/... object used there
    @param object fileInfo object of the file where the usage was found
    @param int lineNumber file line number where the usage was found
    @param string otype object type of the used object
    """
    uType,uObj = findUsingObject(fileInfo,lineNumber)

    # check for what_used
    if uType != 'trigger': # triggers are not "used", they are "fired"
        if fileInfo.fileName not in objectInfo.whereUsed.keys():
            objectInfo.whereUsed[fileInfo.fileName] = []
        objectInfo.whereUsed[fileInfo.fileName].append((fileInfo, lineNumber, uType, uObj))
    # generate a unique number for use in making where used file if needed
    if objectInfo.uniqueNumber == 0: objectInfo.uniqueNumber = metaInfo.NextIndex()
    if uType in ['sequence','tab']: # these objects are not using other objects
        return

    # now care for the what_used
    if uType != 'file':
      if otype in ['view','mview','pkg','synonym','sequence','tab','trigger','type','form']:
        fname = objectInfo.parent.fileName
        finfo = objectInfo.parent
      elif otype in ['func','proc']:
        try: # pkg
            fname = objectInfo.parent.parent.fileName
            finfo = objectInfo.parent.parent
        except: # stand-alone
            logger.info('-> Parsing what_used for %s %s',otype,objectInfo.name) # OI! Never happens?
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
      if not (finfo, objectInfo.lineNumber, otype, objectInfo) in uObj.whatUsed[fname]:
        uObj.whatUsed[fname].append((finfo, objectInfo.lineNumber, otype, objectInfo))
      if uObj.uniqueNumber == 0: uObj.uniqueNumber = metaInfo.NextIndex()
      if uType in ['func','proc'] and hasattr(uObj.parent,'whatUsed'): # add the info to pkg as well
        if finfo.fileName not in uObj.parent.whatUsed.keys():
            uObj.parent.whatUsed[finfo.fileName] = []
        if not (finfo, objectInfo.lineNumber, otype, objectInfo) in uObj.parent.whatUsed[finfo.fileName]:
          uObj.parent.whatUsed[finfo.fileName].append((finfo, objectInfo.lineNumber, otype, objectInfo))
        if uObj.parent.uniqueNumber == 0: uObj.parent.uniqueNumber = metaInfo.NextIndex()

    # handle depgraph info
    if metaInfo.indexPage['depgraph'] and otype in metaInfo.depGraphObjects \
      and uObj.lineNumber != -1 \
      and not objectInfo.javadoc.private and not uObj.javadoc.private:
        # basic: file -> file
        if otype in ['proc','func'] and type(objectInfo.parent).__name__=='PackageInfo': oto = objectInfo.parent.parent.fileName
        else: oto = objectInfo.parent.fileName
        oto = os.path.split(oto)[1]
        ofrom = os.path.split(fileInfo.fileName)[1]
        dep = '"' + ofrom + '" -> "' + oto + '";'
        if not dep in metaInfo.depGraph['file2file']:
            metaInfo.depGraph['file2file'].append(dep)
        # medium: object -> file
        if uType in ['proc','func'] and type(uObj.parent).__name__=='PackageInfo': uname = uObj.parent.name.lower() + '.' + uObj.name.lower()
        else: uname = uObj.name.lower()
        dep = '"' + uname + '" -> "' + oto + '";'
        if not dep in metaInfo.depGraph['object2file']:
            metaInfo.depGraph['object2file'].append(dep)
            try: # might fail due to inline-comments
                props = '"' + uname + '" [color="'+metaInfo.colors[uType][0]+'",fontcolor="'+metaInfo.colors[uType][1] + '"];'
                if not props in metaInfo.depGraph['object2file']:
                    metaInfo.depGraph['object2file'].append(props)
            except:
                logger.debug(_('DepGraph: could not set properties from element %s to file %s line %d'),uObj.name or '<unknown>',oto,lineNumber)
        # medium: file -> object
        if otype in ['proc','func'] and type(objectInfo.parent).__name__=='PackageInfo': oto = objectInfo.parent.name.lower() + '.' + objectInfo.name.lower()
        else: oto = objectInfo.name.lower()
        dep = '"' + ofrom + '" -> "' + oto + '";'
        if not dep in metaInfo.depGraph['file2object']:
            metaInfo.depGraph['file2object'].append(dep)
            try:
                props = '"' + uname + '" [color="'+metaInfo.colors[uType][0]+'",fontcolor="'+metaInfo.colors[uType][1] + '"];'
                if not props in metaInfo.depGraph['file2object']:
                    metaInfo.depGraph['file2object'].append(props)
                props = '"' + oto + '" [color="'+metaInfo.colors[otype][0]+'",fontcolor="'+metaInfo.colors[otype][1] + '"];'
                if not props in metaInfo.depGraph['file2object']:
                    metaInfo.depGraph['file2object'].append(props)
            except:
                logger.debug(_('DepGraph: could not set properties for element %s (to file %s)'),uObj.name or '<unknown>',oto)
        # full: object -> object
        if otype in ['proc','func'] and type(objectInfo.parent).__name__=='PackageInfo': oname = objectInfo.parent.name.lower() + '.' + objectInfo.name.lower()
        else: oname = objectInfo.name.lower()
        dep = '"' + uname + '" -> "' + oname + '";'
        if not dep in metaInfo.depGraph['object2object']:
            metaInfo.depGraph['object2object'].append(dep)
            try:
                props = '"' + uname + '" [color="'+metaInfo.colors[uType][0]+'",fontcolor="'+metaInfo.colors[uType][1] + '"];'
                if not props in metaInfo.depGraph['object2object']:
                    metaInfo.depGraph['object2object'].append(props)
                props = '"' + oname + '" [color="'+metaInfo.colors[otype][0]+'",fontcolor="'+metaInfo.colors[otype][1] + '"];'
                if not props in metaInfo.depGraph['object2object']:
                    metaInfo.depGraph['object2object'].append(props)
                props = '"' + oto + '" [color="'+metaInfo.colors[otype][0]+'",fontcolor="'+metaInfo.colors[otype][1] + '"];'
                if not props in metaInfo.depGraph['file2object']:
                    metaInfo.depGraph['file2object'].append(props)
            except:
                logger.debug(_('DepGraph: could not set properties for objects %s/%s'),uObj.name or '<unknown>',objectInfo.name or '<unknown>')



#------------------------------------------------------------------------------
def ScanFilesForUsage():
    """
    Scans files collected in metaInfo.fileInfoList and checks them line by line
    with metaInfo.<object>list for calls to those objects. If it finds any, it
    updates <object>list where_used and what_used properties accordingly.
    """
    pbarInit(_("Scanning source files for where views and packages are used"),0,len(metaInfo.fileInfoList), logname)

    if metaInfo.indexPage['form'] != '' and metaInfo.useCache: cache = hypercore.cache.cache(metaInfo.cacheDirectory)

    if metaInfo.scanInString: logger.info(_('Including strings in where_used scan'))
    else:                     logger.info(_('Excluding strings from where_used scan'))

    outerfileInfoList = []
    for file_info in metaInfo.fileInfoList:
        outerfileInfoList.append(file_info)

    i = 0
    for outer_file_info in outerfileInfoList:
        # update progressbar
        i += 1
        pbarUpdate(i)

        if outer_file_info.fileType == 'xml':
            formcode = ''
            if metaInfo.useCache:
                try:
                    formcode = cache.get(outer_file_info.fileName,'formcode')
                except:
                    formcode = ''
            else:
                formcode = '' ### need to re-create in case caching is turned off
            fileLines = formcode.split('\n')
        else:
            infile = fopen(outer_file_info.fileName, "r", metaInfo.encoding)
            fileLines = infile.readlines()
            infile.close()

        # if we find a package definition, this flag tells us to also look for
        # functions and procedures.  If we don't find a package definition, there
        # is no reason to look for them
        package_count = -1
        in_block_comment = 0
        new_file = 1
        new_text = ''

        for lineNumber in range(len(fileLines)):

            if new_file == 1:
                token_list = fileLines[lineNumber].split()
            else:
                token_list = token_list1

            # len()-1 because we start with index 0
            if len(fileLines)-1 > lineNumber and not metaInfo.scanInString:
                fileLines[lineNumber+1], matched_string = eatStrings(fileLines[lineNumber+1])
                token_list1 = fileLines[lineNumber+1].split()
            else:
                token_list1 = []
            new_file = 0

            # Skip empty lines
            if len(token_list) < 1:
                new_text += '\n'
                continue

            # ignore lines that begin with comments
            if token_list[0][:2] == "--" or token_list[0][:2] == "//" or token_list[0][:2] == "##":
                new_text += '\n'
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
                new_text += '\n'
                continue
            if token_list[0].upper() in ['PROMPT','GRANT']:
                # that's no usage
                new_text += '\n'
                continue

            # usage only, no creates, replace, force views packages functions or procedures
            # we are scanning a LINE for USAGE - so if we find a CREATE on the line, having
            # a usage on the very same line is out of the question
            usage_flag = 1
            for token_index in range(len(token_list)):

                # CREATE [OR REPLACE] TYPE
                if metaInfo.indexPage['type'] and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "TYPE" \
                and token_list[token_index].upper() in ['CREATE','REPLACE','DROP','ALTER']:
                    # we are creating, dropping, altering, or commenting - not using.  Set flag to 0
                    usage_flag = 0

                # CREATE [OR REPLACE] TRIGGER
                if metaInfo.indexPage['trigger'] and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "TRIGGER" \
                and token_list[token_index].upper() in ['CREATE','REPLACE','DROP','ALTER']:
                    # we are creating, dropping, altering, or commenting - not using.  Set flag to 0
                    usage_flag = 0

                # CREATE [GLOBAL TEMPORARY] TABLE
                if metaInfo.indexPage['tab'] and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "TABLE" \
                and token_list[token_index].upper() in ['CREATE','TEMPORARY','DROP','ALTER']:
                    # we are creating, dropping, or altering - not using.  Set flag to 0
                    usage_flag = 0

                # check for COMMENT ON (COLUMN | TABLE | MATERIALIZED VIEW | INDEXTYPE | OPERATOR | MINING MODEL)
                if metaInfo.indexPage['tab'] != '' and len(token_list) > token_index+1 and token_index > 0 \
                and token_list[token_index+1].upper() in ['COLUMN','TABLE','INDEXTYPE','OPERATOR','MINING','MATERIALIZED'] \
                and token_list[token_index].upper() == "ON" \
                and token_list[token_index-1].upper() == "COMMENT":
                    # we are just commenting on a table column
                    usage_flag = 0

                # look for CREATE INDEX
                if metaInfo.indexPage['tab'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "INDEX" \
                and token_list[token_index].upper() == "CREATE":
                    # we don't consider index creation as usage for tables
                    usage_flag = 0

                # look for CREATE VIEW, REPLACE VIEW, FORCE VIEW
                if metaInfo.indexPage['view'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "VIEW" \
                and token_list[token_index].upper() in ['CREATE','REPLACE','FORCE']:
                    # we are creating, forcing, or replacing - not using.  Set flag to 0
                    usage_flag = 0

                # look for CREATE MATERIALIZED VIEW
                if metaInfo.indexPage['mview'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "VIEW" \
                and token_list[token_index].upper() == "MATERIALIZED":
                    # we are creating (or possibly dropping) - not using.  Set flag to 0
                    usage_flag = 0

                # look for sequences
                if metaInfo.indexPage['sequence'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "SEQUENCE" \
                and token_list[token_index].upper() in ['CREATE','DROP','ALTER']:
                    # we are creating, altering, or dropping - not using.  Set flag to 0
                    usage_flag = 0

                # CREATE SYNONYMs
                if metaInfo.indexPage['synonym'] != '' and len(token_list) > token_index+1 \
                and token_list[token_index+1].upper() == "SYNONYM" \
                and token_list[token_index].upper() in ['CREATE','REPLACE','DROP','PUBLIC']:
                    # we are creating, or dropping - not using.  Set flag to 0
                    usage_flag = 0

                # PACKAGE (CREATE|ALTER|DROP)
                if token_list[token_index].upper() == "PACKAGE" \
                and len(token_list) > token_index+2:
                    #and token_list[token_index+1].upper() == "BODY": # commented out - creates trouble if package spec is in the same file
                    usage_flag = 0

                # look for stand-alone functions and procedures (those of the packages are
                # already excluded in the previous step)
                if token_index>0 and token_list[token_index].upper() == "FUNCTION" and token_list[token_index-1] in ['CREATE','REPLACE']:
                    usage_flag = 0
                # look for procedures
                if token_index>0 and token_list[token_index].upper() == "PROCEDURE" and token_list[token_index-1] in ['CREATE','REPLACE']:
                    usage_flag = 0

                # look for END x
                if token_list[token_index].upper() == "END" \
                and len(token_list) > token_index+1:
                    usage_flag = 0


            if usage_flag == 0: # this line holds some CREATE statement, no USAGE
                new_text += '\n'
            else:
                new_text += fileLines[lineNumber]

        # Loop through all previously found views and packages to see if they are used in this line of text
        for inner_file_info in metaInfo.fileInfoList:

            # if this FileInfo instance has types
            for elem in inner_file_info.typeInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'type')

            # if this FileInfo instance has triggers
            for elem in inner_file_info.triggerInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'trigger')

            # if this FileInfo instance has tables
            for elem in inner_file_info.tabInfoList:
                # perform case insensitive find
                try:
                    res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                except:
                    logger.error('RegExp error searching for "'+tab_info.name+'"')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'tab')

            # if this FileInfo instance has views
            for elem in inner_file_info.viewInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'view')

            # if this FileInfo instance has materialized views
            for elem in inner_file_info.mviewInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'mview')

            # if this FileInfo instance has synonyms
            for elem in inner_file_info.synInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'synonym')

            # if this FileInfo instance has sequences
            for elem in inner_file_info.seqInfoList:
                # perform case insensitive find
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'sequence')

            # if this FileInfo instance has stand-alone functions
            for elem in inner_file_info.functionInfoList:
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'function')

            # if this FileInfo instance has stand-alone procedures
            for elem in inner_file_info.procedureInfoList:
                res = getWordLineNr(new_text,'\\b'+elem.name+'\\b')
                for ires in res:
                    addWhereUsed(elem, outer_file_info, ires[0], 'procedure')

            # if this FileInfo instance has packages
            for package_info in inner_file_info.packageInfoList:

                # perform case insensitive find, this is "package name"."function or procedure name"
                res = getWordLineNr(new_text,'\\b'+package_info.name+'\\.\S')
                if len(res):
                    for ires in res:
                        addWhereUsed(package_info, outer_file_info, ires[0], 'pkg')

                    #look for any of this packages' functions
                    for function_info in package_info.functionInfoList:
                        res = getWordLineNr(new_text,'\\b'+package_info.name+'\.'+function_info.name+'\\b')
                        for ires in res:
                            addWhereUsed(function_info, outer_file_info, ires[0], 'func')

                    #look for any of this packages procedures
                    for procedure_info in package_info.procedureInfoList:
                        res = getWordLineNr(new_text,'\\b'+package_info.name+'\.'+procedure_info.name+'\\b')
                        for ires in res:
                            addWhereUsed(procedure_info, outer_file_info, ires[0], 'proc')

                ### File internal references - possible calls without a package_name
                if outer_file_info.uniqueNumber == inner_file_info.uniqueNumber and metaInfo.scanShortRefs:

                    #look for any of this packages' functions
                    for function_info in package_info.functionInfoList:
                        res = getWordLineNr(new_text,'(^|\\s|[(;,])'+function_info.name+'([ (;,)]|$)')
                        for ires in res:
                            if not (fileLines[ires[0]].find('--') > -1 and fileLines[ires[0]].find('--') < ires[1]): # check for inline comments to be excluded
                                addWhereUsed(package_info, outer_file_info, ires[0], 'pkg')
                                addWhereUsed(function_info, outer_file_info, ires[0], 'func')

                    #look for any of this packages procedures
                    for procedure_info in package_info.procedureInfoList:
                        res = getWordLineNr(new_text,'(^|\\s|[(;,])'+procedure_info.name+'([ (;,)]|$)')
                        for ires in res:
                            if not (fileLines[ires[0]].find('--') > -1 and fileLines[ires[0]].find('--') < ires[1]): # check for inline comments to be excluded
                                addWhereUsed(package_info, outer_file_info, ires[0], 'pkg')
                                addWhereUsed(procedure_info, outer_file_info, ires[0], 'proc')

    # complete line on task completion
    pbarClose()
