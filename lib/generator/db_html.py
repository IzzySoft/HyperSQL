"""
Database-specific HTML stuff
"""
__revision__ = '$Id$'

import time # for makeHTMLFooter
import os
from hypercore.elements import metaInfo
from hypercore.helpers  import TupleCompareFirstElements # WriteObjectList()
from .commonhtml import getDualCodeLink,makeDualCodeRef,makeUsageCol,MakeHTMLHeader,MakeHTMLFooter
from progress import *
from iz_tools.system import fopen
import hypercore.cache # for HyperLinkedSourceFilePages

# Setup gettext support
import gettext
from hypercore.gettext_init import langpath, langs
gettext.bindtextdomain('hypersql', langpath)
gettext.textdomain('hypersql')
lang = gettext.translation('hypersql', langpath, languages=langs, fallback=True)
_ = lang.ugettext


# Setup logging
from hypercore.logger import logg
logname = 'GenHTML'
logger = logg.getLogger(logname)

#------------------------------------------------------------------------------
def MakeMethodIndex(objectType):
    """
    Generate HTML index page for all package elements of the specified objectType
    @param string objectType one of 'function', 'procedure'
    """

    if objectType not in ['function','procedure']: # not a valid/supported objectType
        return
    if metaInfo.indexPage[objectType] == '':       # index for this objectType is turned off
        return

    printProgress(_('Creating %s index') % _(objectType.capitalize()), logname)

    objectTupleList = []
    if objectType == 'function':
        html_title   = _('Index Of All Functions')
        object_name  = _('Function')
    else:
        html_title   = _('Index Of All Procedures')
        object_name  = _('Procedure')
    for file_info in metaInfo.fileInfoList:
        if file_info.fileType != "sql": # skip all non-sql files
            continue
        if objectType == 'function':
            for fi in file_info.functionInfoList:
                objectTupleList.append((fi.name.upper(), fi, file_info, None))
        else:
            for fi in file_info.procedureInfoList:
                objectTupleList.append((fi.name.upper(), fi, file_info, None))
        for package_info in file_info.packageInfoList:
            if objectType == 'function':
                elemInfoList = package_info.functionInfoList
            else:
                elemInfoList = package_info.procedureInfoList
            for elem_info in elemInfoList:
                objectTupleList.append((elem_info.name.upper(), elem_info, file_info, package_info)) # append as tuple for case insensitive sort
    objectTupleList.sort(TupleCompareFirstElements)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage[objectType]), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader(objectType))
    outfile.write("<H1>"+html_title+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_(object_name)+"</TH><TH>"+_('from package')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Usage')+"</TH></TR>\n")
    i = 0

    for object_tuple in objectTupleList: # list of tuples describing every object
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(object_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        # Write column 1: Object name w/ links
        outfile.write("  <TR"+trclass+"><TD>" + object_tuple[1].javadoc.getVisibility() + makeDualCodeRef(HTMLref,HTMLjref,object_tuple[1].name.lower(),object_tuple[2].bytes) + "</TD>")
        # Write column 2: Package name w/ links
        if object_tuple[3] is None:
          outfile.write("<TD>&nbsp;</TD>")
        else:
          outfile.write("<TD>" + makeDualCodeRef(HTMLpref,HTMLpjref,object_tuple[3].name.lower(),object_tuple[2].bytes) + "</TD>")
        # Write column 3: Short description
        outfile.write("<TD>" + object_tuple[1].javadoc.getShortDesc() + "</TD>")
        # Write column 4: where_used / what_used
        outfile.write( makeUsageCol(len(object_tuple[1].whereUsed.keys())>0,len(object_tuple[1].whatUsed.keys())>0,object_tuple[1].uniqueNumber,'',len(object_tuple[1].javadoc.used)>0,len(object_tuple[1].javadoc.uses)>0) )
        outfile.write("</TR>\n")
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter(objectType))
    outfile.close()


#------------------------------------------------------------------------------
def MakeElemIndex(objectType):
    """
    Generate HTML index page for all tables, (m)views, synonyms, sequences or
    triggers
    @param string objectType what the index should be created for?
           ('tab','view','mview','synonym','sequence','trigger')
    """

    if objectType not in ['tab','view','mview','synonym','sequence','trigger']: # not a valid/supported objectType
        return
    if metaInfo.indexPage[objectType] == '': # Index was turned off
        return

    if objectType == 'tab':
        printProgress(_("Creating %s index") % _('Table'), logname)
    else:
        printProgress(_("Creating %s index") % _(objectType.capitalize()), logname)

    if objectType == 'trigger':
      html_title = _('Index Of All Triggers')
      object_name = _('Trigger')
    elif objectType == 'tab':
      html_title = _('Index Of All Tables')
      object_name = _('Table')
    elif objectType == 'view':
      html_title = _('Index Of All Views')
      object_name = _('View')
    elif objectType == 'mview':
      html_title = _('Index Of All Materialized Views')
      object_name = _('Materialized View')
    elif objectType == 'sequence':
      html_title = _('Index Of All Sequences')
      object_name = _('Sequence')
    elif objectType == 'synonym':
      html_title = _('Index Of All Synonyms')
      object_name = _('Synonym')
    else:
      html_title = _('Index for unknown object type %s', objectType)
      object_name = _('Object')

    objectTupleList = []
    for file_info in metaInfo.fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue        
        if objectType == 'trigger':
          objectList = file_info.triggerInfoList
        elif objectType == 'tab':
          objectList = file_info.tabInfoList
        elif objectType == 'view':
          objectList = file_info.viewInfoList
        elif objectType == 'mview':
          objectList = file_info.mviewInfoList
        elif objectType == 'sequence':
          objectList = file_info.seqInfoList
        else:
          objectList = file_info.synInfoList
        for object_info in objectList:
            objectTupleList.append((object_info.name.upper(), object_info, file_info)) # append as tuple for case insensitive sort

    objectTupleList.sort(TupleCompareFirstElements)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage[objectType]), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader(objectType))
    outfile.write('<H1>'+html_title+'</H1>\n')
    outfile.write('<TABLE CLASS="apilist">\n')
    outfile.write('  <TR><TH>'+object_name+'</TH><TH>'+_('Details')+'</TH><TH>'+_('Usage')+'</TH></TR>\n')
    i = 0

    for object_tuple in objectTupleList: # list of tuples describing every object
        trclass = ' CLASS="tr'+`i % 2`+'"'
        if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or object_tuple[2].bytes <= metaInfo.includeSourceLimit ):
            HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(object_tuple)
            name = makeDualCodeRef(HTMLref,HTMLjref,object_tuple[1].name.lower(),object_tuple[2].bytes)
            outfile.write('  <TR'+trclass+'><TD>' + name + '</TD>')
        else:
            outfile.write('  <TR'+trclass+'><TD>' + object_tuple[1].name.lower() + '</TD>')
        outfile.write('<TD>' + object_tuple[1].javadoc.getShortDesc() + '</TD>')
        outfile.write( makeUsageCol(len(object_tuple[1].whereUsed.keys())>0,len(object_tuple[1].whatUsed.keys())>0,object_tuple[1].uniqueNumber,'',len(object_tuple[1].javadoc.used)>0,len(object_tuple[1].javadoc.uses)>0) )
        outfile.write('</TR>\n')
        i += 1

    outfile.write('</TABLE>\n')
    outfile.write(MakeHTMLFooter(objectType))
    outfile.close()


#------------------------------------------------------------------------------
def WriteObjectList(oTupleList, listName, objectName, outfile):
    """
    Write info for objects contained in packages/forms on full_list pages
    (helper to MakeFormIndexWithUnits and MakePackagesWithFuncsAndProcsIndex)
    @param list oTupleList list of tuples (name,object,file_info)
    @param string listName name for the table heading
    @param string objectName same in singular form for the object itself
    @param object outfile handler to the output HTML file
    """
    oTupleList.sort(TupleCompareFirstElements)
    if len(oTupleList) != 0:
        outfile.write('  <TR><TH class="sub" COLSPAN="3">' + listName + '</TH></TR>\n  <TR><TD COLSPAN="3">')
        outfile.write('<TABLE ALIGN="center">\n')
        outfile.write('    <TR><TD ALIGN="center"><B>' + objectName + '</B></TD><TD ALIGN="center"><B>Details</B></TD><TD ALIGN="center"><B>'+_('Usage')+'</B></TD></TR>\n')
    i = 0
    for oTuple in oTupleList:
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(oTuple)
        if type(oTuple[1]).__name__ == 'FormInfo': codesize = oTuple[1].codesize
        else: codesize = oTuple[2].bytes
        outfile.write('    <TR CLASS="tr'+`i % 2`+'"><TD>' + oTuple[1].javadoc.getVisibility() \
          + makeDualCodeRef(HTMLref,HTMLjref, oTuple[1].name.lower(),codesize) + '</TD>\n')
        outfile.write('<TD>' + oTuple[1].javadoc.getShortDesc() + '</TD>')
        outfile.write( makeUsageCol(len(oTuple[1].whereUsed.keys())>0,len(oTuple[1].whatUsed.keys())>0,oTuple[1].uniqueNumber,'',len(oTuple[1].javadoc.used)>0,len(oTuple[1].javadoc.uses)>0) )
        outfile.write('</TR>\n')
        i += 1
    if len(oTupleList) != 0:
        outfile.write('</TABLE></TD></TR>\n')


#===============================================================[ Packages ]===
#------------------------------------------------------------------------------
def MakePackageIndex():
    """Generate HTML index page for all packages"""

    if metaInfo.indexPage['package'] == '':
        return

    printProgress(_('Creating package index'), logname)

    packagetuplelist = []
    for file_info in metaInfo.fileInfoList:
        # skip all non-sql files
        if file_info.fileType != 'sql':
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage['package']), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader('package'))
    outfile.write('<H1>'+_('Index Of All Packages')+'</H1>\n')
    outfile.write('<TABLE CLASS="apilist">\n')
    outfile.write('  <TR><TH>'+_('Package')+'</TH><TH>'+_('Details')+'</TH><TH>'+_('Usage')+'</TH></TR>\n')
    i = 0

    for package_tuple in packagetuplelist: # list of tuples describing every package file name and line number as an HTML reference
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        outfile.write('  <TR'+trclass+'><TD>' + makeDualCodeRef(HTMLref,HTMLjref,package_tuple[1].name.lower(),package_tuple[2].bytes) + '</TD>')
        outfile.write('<TD>' + package_tuple[1].javadoc.getShortDesc() + '</TD>')
        outfile.write( makeUsageCol(len(package_tuple[1].whereUsed.keys())>0,len(package_tuple[1].whatUsed.keys())>0,package_tuple[1].uniqueNumber,'',len(package_tuple[1].javadoc.used)>0,len(package_tuple[1].javadoc.uses)>0) )
        outfile.write('</TR>\n')
        i += 1

    outfile.write('</TABLE>\n')
    outfile.write(MakeHTMLFooter('package'))
    outfile.close()


#------------------------------------------------------------------------------
def MakePackagesWithFuncsAndProcsIndex():
    """Generate HTML index page for all packages, including their functions and procedures"""

    if metaInfo.indexPage['package_full'] == '':
        return

    printProgress(_('Creating "package with functions and procedures" index'), logname)

    packagetuplelist = []
    for file_info in metaInfo.fileInfoList:
        # skip all non-sql files
        if file_info.fileType != 'sql':
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort

    packagetuplelist.sort(TupleCompareFirstElements)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage['package_full']), 'w', metaInfo.encoding)
    outfile.write(MakeHTMLHeader('package_full'))
    outfile.write('<H1>'+_('Index Of All Packages, Their Functions And Procedures')+'</H1>\n')

    for package_tuple in packagetuplelist:
        # file name and line number as an HTML reference
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(package_tuple)
        outfile.write('<TABLE CLASS="apilist" WIDTH="98%">\n  <TR><TH COLSPAN="3">' + package_tuple[1].name.lower() + '</TH></TR>\n')
        outfile.write('  <TR><TD ALIGN="center" WIDTH="33.33%">')
        if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or package_tuple[2].bytes <= metaInfo.includeSourceLimit ):
            outfile.write('<A href="' + HTMLref + '">'+_('Code')+'</A>')
        else:
            outfile.write('&nbsp;')
        outfile.write('</TD><TD ALIGN="center" WIDTH="33.34%">')
        if HTMLjref == '':
            outfile.write('&nbsp;')
        else:
            outfile.write('<A HREF="' + HTMLjref + '">'+_('ApiDoc')+'</A>')
        outfile.write('</TD>' + makeUsageCol(len(package_tuple[1].whereUsed.keys())>0,len(package_tuple[1].whatUsed.keys())>0,package_tuple[1].uniqueNumber,' WIDTH="33.33%"',len(package_tuple[1].javadoc.used)>0,len(package_tuple[1].javadoc.uses)>0))
        outfile.write('</TR>\n')

        # functions in this package
        functiontuplelist = []
        for function_info in package_tuple[1].functionInfoList:
            functiontuplelist.append((function_info.name.upper(), function_info, package_tuple[2])) # append as tuple for case insensitive sort
        WriteObjectList(functiontuplelist, _('Functions'), _('Function'), outfile)

        # procedures in this package
        proceduretuplelist = []
        for procedure_info in package_tuple[1].procedureInfoList:
            proceduretuplelist.append((procedure_info.name.upper(), procedure_info, package_tuple[2])) # append as tuple for case insensitive sort
        WriteObjectList(proceduretuplelist, _('Procedures'), _('Procedure'), outfile)

        outfile.write("</TABLE>\n")

    outfile.write(MakeHTMLFooter('package_full'))
    outfile.close()


#===========================================================[ Oracle Forms ]===
#------------------------------------------------------------------------------
def MakeFormIndex():
    """
    Generate HTML index page for Oracle Forms
    """
    if metaInfo.indexPage['form'] == '': return     # Forms disabled = nothing to do here
    printProgress(_('Creating %s index') % 'Form', logname)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage['form']), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader('form'))
    outfile.write("<H1>"+_('Index Of All Forms')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    outfile.write("  <TR><TH>"+_('Form')+"</TH><TH>"+_('Details')+"</TH><TH>"+_('Usage')+"</TH></TR>\n")

    formtuplelist = []
    for file_info in metaInfo.fileInfoList:
        if file_info.fileType != "xml": # skip all non-xml files
            continue

        for form_info in file_info.formInfoList:
            formtuplelist.append((form_info.name.upper(), form_info, file_info))

    formtuplelist.sort(TupleCompareFirstElements)

    i = 0
    for formtuple in formtuplelist:
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(formtuple)
        trclass = ' CLASS="tr'+`i % 2`+'"'
        outfile.write('  <TR'+trclass+'><TD>' + makeDualCodeRef(HTMLref,HTMLjref,formtuple[1].name.lower(),formtuple[1].codesize) + '</TD>')
        detail = formtuple[1].javadoc.getShortDesc() or formtuple[1].title
        outfile.write('<TD>' + detail + '</TD>')
        outfile.write( makeUsageCol(len(formtuple[1].whereUsed.keys())>0,len(formtuple[1].whatUsed.keys())>0,formtuple[1].uniqueNumber,'',len(formtuple[1].javadoc.used)>0,len(formtuple[1].javadoc.uses)>0) )
        outfile.write('</TR>\n')
        i += 1

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter('form'))
    outfile.close()


#------------------------------------------------------------------------------
def MakeFormIndexWithUnits():
    """
    Generate HTML index page for Oracle Forms
    """
    if metaInfo.indexPage['form_full'] == '': return     # Forms disabled = nothing to do here
    printProgress(_('Creating full form index'), logname)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage['form_full']), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader('form_full'))
    outfile.write("<H1>"+_('Index of all Forms including their ProgramUnits')+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")

    for file_info in metaInfo.fileInfoList:
        if file_info.fileType != "xml": # skip all non-xml files
            continue

        packagetuplelist   = []
        functiontuplelist  = []
        proceduretuplelist = []

        form_info = file_info.formInfoList[0] # there is only one form per file
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink((form_info.name.upper(),form_info,file_info))
        outfile.write(' <TR><TH COLSPAN="3">' + form_info.name.lower() + '</TH></TR>\n')
        outfile.write('  <TR><TD ALIGN="center" WIDTH="33.33%">')
        if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or form_info.codesize <= metaInfo.includeSourceLimit ):
            outfile.write('<A href="' + HTMLref + '">'+_('Code')+'</A>')
        else:
            outfile.write('&nbsp;')
        outfile.write('</TD><TD ALIGN="center" WIDTH="33.34%">')
        if HTMLjref == '':
            outfile.write('&nbsp;')
        else:
            outfile.write('<A HREF="' + HTMLjref + '">'+_('ApiDoc')+'</A>')
        outfile.write('</TD>' + makeUsageCol(len(form_info.whereUsed.keys())>0,len(form_info.whatUsed.keys())>0,form_info.uniqueNumber,' WIDTH="33.33%"',len(form_info.javadoc.used)>0,len(form_info.javadoc.uses)>0))
        outfile.write('</TR>\n')

        if len(form_info.packageInfoList) > 0:
          for itemInfo in form_info.packageInfoList:
            packagetuplelist.append((itemInfo.name.upper(),itemInfo,file_info))
          WriteObjectList(packagetuplelist, _('Packages'), _('Package'), outfile)
        if len(form_info.functionInfoList) > 0:
          for itemInfo in form_info.functionInfoList:
            functiontuplelist.append((itemInfo.name.upper(),itemInfo,file_info))
          WriteObjectList(functiontuplelist, _('Functions'), _('Function'), outfile)
        if len(form_info.procedureInfoList) > 0:
          for itemInfo in form_info.procedureInfoList:
            proceduretuplelist.append((itemInfo.name.upper(),itemInfo,file_info))
          WriteObjectList(proceduretuplelist, _('Procedures'), _('Procedure'), outfile)

    outfile.write("</TABLE>\n")
    outfile.write(MakeHTMLFooter('form_full'))
    outfile.close()


#==============================================================[ TaskLists ]===
#------------------------------------------------------------------------------
def MakeTaskList(taskType):
    """
    Generate HTML page for all tasks of the specified type found in JavaDoc comments
    @param string taskType Type of the task - one of 'bug', 'todo'
    """

    if taskType not in ['bug','todo','report']:
        return

    if metaInfo.indexPage[taskType] == '':
        return

    printProgress(_("Creating %s list") % _(taskType.capitalize()), logname)

    def appendStandAloneItems(xtuple,headname):
        if taskType == 'bug':
            task = xtuple[1].bugs
        elif taskType == 'todo':
            task = xtuple[1].todo
        else:
            task = xtuple[1].verification
        if task.allItemCount() < 1:
            return
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(xtuple)
        if type(xtuple[1]).__name__ == 'FormInfo': codesize = xtuple[1].codesize
        else: codesize = xtuple[2].bytes
        outfile.write('  <TR><TH COLSPAN="2">' + headname + ' ' + makeDualCodeRef(HTMLref,HTMLjref,xtuple[1].name.lower(),codesize) + '</TH></TR>\n');
        outfile.write('  <TR><TD COLSPAN="2">' + task.getHtml() + '</TD></TR>\n')
        outfile.write('  <TR><TD COLSPAN="2"><DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV></TD></TR>\n')

    packagetuplelist   = []
    tabletuplelist     = []
    viewtuplelist      = []
    mviewtuplelist     = []
    syntuplelist       = []
    seqtuplelist       = []
    triggertuplelist   = []
    functiontuplelist  = []
    proceduretuplelist = []
    formtuplelist      = []
    for file_info in metaInfo.fileInfoList:
        # skip all non-sql files
        if file_info.fileType not in ['sql','xml']:
            continue        
        for package_info in file_info.packageInfoList:
            packagetuplelist.append((package_info.name.upper(), package_info, file_info)) # append as tuple for case insensitive sort
        for tabInfo in file_info.tabInfoList:
            tabletuplelist.append((tabInfo.name.upper(), tabInfo, file_info))
        for viewInfo in file_info.viewInfoList:
            viewtuplelist.append((viewInfo.name.upper(), viewInfo, file_info))
        for mviewInfo in file_info.mviewInfoList:
            mviewtuplelist.append((mviewInfo.name.upper(), mviewInfo, file_info))
        for synInfo in file_info.synInfoList:
            syntuplelist.append((synInfo.name.upper(), synInfo, file_info))
        for seqInfo in file_info.seqInfoList:
            seqtuplelist.append((seqInfo.name.upper(), seqInfo, file_info))
        for triggerInfo in file_info.triggerInfoList:
            triggertuplelist.append((triggerInfo.name.upper(), triggerInfo, file_info))
        for functionInfo in file_info.functionInfoList:
            functiontuplelist.append((functionInfo.name.upper(), functionInfo, file_info))
        for procInfo in file_info.procedureInfoList:
            proceduretuplelist.append((procInfo.name.upper(), procInfo, file_info))
        for formInfo in file_info.formInfoList:
            formtuplelist.append((formInfo.name.upper(), formInfo, file_info))

    packagetuplelist.sort(TupleCompareFirstElements)
    tabletuplelist.sort(TupleCompareFirstElements)
    viewtuplelist.sort(TupleCompareFirstElements)
    mviewtuplelist.sort(TupleCompareFirstElements)
    syntuplelist.sort(TupleCompareFirstElements)
    seqtuplelist.sort(TupleCompareFirstElements)
    triggertuplelist.sort(TupleCompareFirstElements)
    functiontuplelist.sort(TupleCompareFirstElements)
    proceduretuplelist.sort(TupleCompareFirstElements)
    formtuplelist.sort(TupleCompareFirstElements)

    outfile = fopen(os.path.join(metaInfo.htmlDir,metaInfo.indexPage[taskType]), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader(taskType))
    if taskType == 'bug':
        outfile.write('<H1>'+_('List of open Bugs')+'</H1>\n')
    elif taskType == 'todo':
        outfile.write('<H1>'+_('List of things ToDo')+'</H1>\n')
    else:
        outfile.write('<H1>'+_('JavaDoc Validation Report')+'</H1>\n')
    outfile.write('<TABLE CLASS="apilist">\n')

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
        outfile.write('  <TR><TH COLSPAN="2">' + _('Package') + ' ' + makeDualCodeRef(HTMLref,HTMLjref,package_tuple[1].name.lower(),package_tuple[2].bytes) + '</TH></TR>\n');
        if task.taskCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Package General')+'</I></B></TD></TR>\n')
            outfile.write('  <TR><TD COLSPAN="2">' + task.getHtml() + '</TD></TR>\n')
        if task.funcCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Functions')+'</I></B></TD></TR>\n')
            outfile.write( task.getFuncHtml() )
        if task.procCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Procedures')+'</I></B></TD></TR>\n')
            outfile.write( task.getProcHtml() )
        outfile.write('  <TR><TD COLSPAN="2"><DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV></TD></TR>\n')

    # Walk the stand-alone elements
    for functuple in functiontuplelist: appendStandAloneItems(functuple,_('Function'))
    for proctuple in proceduretuplelist: appendStandAloneItems(proctuple,_('Procedure'))
    for tabletuple in tabletuplelist: appendStandAloneItems(tabletuple,_('Table'))
    for viewtuple in viewtuplelist: appendStandAloneItems(viewtuple,_('View'))
    for viewtuple in mviewtuplelist: appendStandAloneItems(viewtuple,_('MView'))
    for seqtuple in seqtuplelist: appendStandAloneItems(seqtuple,_('Sequence'))
    for seqtuple in syntuplelist: appendStandAloneItems(seqtuple,_('Synonym'))
    for triggertuple in triggertuplelist: appendStandAloneItems(triggertuple,_('Trigger'))

    # Walk the forms
    for formtuple in formtuplelist:
        if taskType == 'bug':
            task = formtuple[1].bugs
        elif taskType == 'todo':
            task = formtuple[1].todo
        else:
            task = formtuple[1].verification
        if task.allItemCount() < 1:
            continue
        HTMLref,HTMLjref,HTMLpref,HTMLpjref = getDualCodeLink(formtuple)
        outfile.write('  <TR><TH COLSPAN="2">' + _('Form') + ' ' + makeDualCodeRef(HTMLref,HTMLjref,formtuple[1].name.lower(),formtuple[1].codesize) + '</TH></TR>\n');
        if task.taskCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Form General')+'</I></B></TD></TR>\n')
            outfile.write('  <TR><TD COLSPAN="2">' + task.getHtml() + '</TD></TR>\n')
        if task.funcCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Functions')+'</I></B></TD></TR>\n')
            outfile.write( task.getFuncHtml() )
        if task.procCount() > 0:
            outfile.write('  <TR><TD COLSPAN="2" ALIGN="center"><B><I>'+_('Procedures')+'</I></B></TD></TR>\n')
            outfile.write( task.getProcHtml() )
        outfile.write('  <TR><TD COLSPAN="2"><DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV></TD></TR>\n')

        if len(task.pkgs)>0: outfile.write( task.getSubPkgHtml() )

    outfile.write('</TABLE>\n')
    outfile.write(MakeHTMLFooter(taskType))
    outfile.close()


#=================================================[ Source and Usage Pages ]===
#------------------------------------------------------------------------------
def CreateHyperlinkedSourceFilePages():
    """
    Generates pages with the complete source code of each file, including link
    targets (A NAME=) for each line. This way we can link directly to the line
    starting the definition of an object, or where it is called (used) from.
    Very basic syntax highlighting is performed here as well if code is included.
    """
    from hypercore.helpers import size_format, num_format
    from hypercore.codeformatter import hypercode
    from sys import argv
    import fileinput, re
    def ObjectDetailsListItem(item,i,fsize,fileInfo):
        """
        Write the row for the overview
        @param object item procedure/function item
        @param int i counter for odd/even row alternation
        @param int fsize code size (to decide whether we link to code)
        @param object fileInfo the corresponding FileInfo object for additional information
        """
        iname = item.javadoc.getVisibility()
        if item.javadoc.name != '' and not item.javadoc.ignore:
            iname += '<A HREF="#'+fileInfo.anchorNames[item.uniqueNumber][0]+'">'+item.javadoc.name+'</A>'
            idesc = item.javadoc.getShortDesc()
        else:
            iname += (item.javadoc.name or item.name)
            idesc = ''
        outfile.write(' <TR CLASS="tr'+`i % 2`+'"><TD><DIV STYLE="margin-left:15px;text-indent:-15px;">'+iname)
        if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or fsize <= metaInfo.includeSourceLimit ):
            outfile.write(' <SUP><A HREF="#L'+str(item.lineNumber)+'">#</A></SUP>')
        outfile.write(' (')
        if len(item.javadoc.params) > 0:
            ph = ''
            for par in item.javadoc.params:
                ph += ', ' + par.name
            outfile.write(ph[2:])
        outfile.write(')</DIV></TD><TD>'+idesc+'</TD>')
        outfile.write( makeUsageCol(len(item.whereUsed.keys())>0,len(item.whatUsed.keys())>0,item.uniqueNumber,'',len(item.javadoc.used)>0,len(item.javadoc.uses)>0) )
        outfile.write('</TR>\n')

    def readCodeFromFile(fInfo):
        """
        read up the source file
        @param object fInfo fileInfo object
        @return list linelist list of code lines
        """
        if fInfo.fileType == 'sql':
            infile = fopen(fInfo.fileName, "r", metaInfo.encoding)
            infile_line_list = infile.readlines()
            infile.close()
        else:
            if metaInfo.useCache:
                try:
                    formcode = cache.get(fInfo.fileName,'formcode')
                except:
                    formcode = ''
            else:
                formcode = '' ### need to re-create in case caching is turned off
            infile_line_list = formcode.split('\n')
            for line in range(len(infile_line_list)): infile_line_list[line] += '\n'
        return infile_line_list

    def formPkgFuncDetails(fu):
        """
        Prepare form package function/procedure details for HTML
        @param object fu ElemInfo object form.packageInfoList[i].functionInfoList[k]
        @return string html
        """
        html  = ' <TR><TD STYLE="text-align:center;font-weight:bold;"><A NAME="'
        html += (fu.javadoc.name or fu.name.lower())
        html += '"></A></TD></TR>\n <TR><TD>'
        html += fu.javadoc.getHtml(file_info.anchorNames[fu.uniqueNumber][0])
        html += '</TD></TR>\n'
        return html

    top_level_directory = metaInfo.topLevelDirectory
    if metaInfo.useCache: cache = hypercore.cache.cache(metaInfo.cacheDirectory)
    pbarInit(_("Creating hyperlinked source file pages"),0,len(metaInfo.fileInfoList), logname)
    if metaInfo.includeSourceLimit > 0:
        logger.info( _('Source code inclusion is limited to files smaller than %s'), size_format(metaInfo.includeSourceLimit,0) )

    sqlkeywords = []
    sqltypes    = []
    for line in fileinput.input(os.path.split(argv[0])[0] + os.sep + 'sql.keywords'):
      if line.strip()[0]=='#':
        continue
      sqlkeywords.append(line.strip())
    for line in fileinput.input(os.path.split(argv[0])[0] + os.sep + 'sql.types'):
      if line.strip()[0]=='#':
        continue
      sqltypes.append(line.strip())

    k = 0
    for file_info in metaInfo.fileInfoList:
        # update progressbar
        k += 1
        pbarUpdate(k)

        # skip all non-sql files
        if file_info.fileType not in ['sql','xml']:
            continue

        # generate a file name for us to write to (+1 for delimiter)
        outfilename = file_info.getHtmlName()

        outfile = fopen(os.path.join(metaInfo.htmlDir,outfilename), "w", metaInfo.encoding)
        outfile.write(MakeHTMLHeader(file_info.fileName[len(top_level_directory)+1:]))
        outfile.write('<H1>' + file_info.fileName[len(top_level_directory)+1:] + '</H1>\n')

        # ===[ JAVADOC STARTS HERE ]===
        file_info.sortLists()
        packagedetails = '\n\n'

        # Do we have tables in this file?
        if len(file_info.tabInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Tables')+'</H2>\n')
            for v in range(len(file_info.tabInfoList)):
                outfile.write(file_info.tabInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.tabInfoList[v].uniqueNumber][0]))

        # Do we have views in this file?
        if len(file_info.viewInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Views')+'</H2>\n')
            for v in range(len(file_info.viewInfoList)):
                outfile.write(file_info.viewInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.viewInfoList[v].uniqueNumber][0]))

        # Do we have mviews in this file?
        if len(file_info.mviewInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Materialized Views')+'</H2>\n')
            for v in range(len(file_info.mviewInfoList)):
                outfile.write(file_info.mviewInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.mviewInfoList[v].uniqueNumber][0]))

        # Do we have synonyms in this file?
        if len(file_info.synInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Synonyms')+'</H2>\n')
            for v in range(len(file_info.synInfoList)):
                outfile.write(file_info.synInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.synInfoList[v].uniqueNumber][0]))

        # Do we have trigger in this file?
        if len(file_info.triggerInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Triggers')+'</H2>\n')
            for v in range(len(file_info.triggerInfoList)):
                outfile.write(file_info.triggerInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.triggerInfoList[v].uniqueNumber][0]))

        # Do we have stand-alone functions?
        if len(file_info.functionInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Functions')+'</H2>\n')
            for v in range(len(file_info.functionInfoList)):
                outfile.write(file_info.functionInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.functionInfoList[v].uniqueNumber][0]))
            
        # Do we have stand-alone procedures?
        if len(file_info.procedureInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Procedures')+'</H2>\n')
            for v in range(len(file_info.procedureInfoList)):
                outfile.write(file_info.procedureInfoList[v].javadoc.getHtml(file_info.anchorNames[file_info.procedureInfoList[v].uniqueNumber][0]))
            
        # Do we have forms in this file?
        if len(file_info.formInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Form Overview')+'</H2>\n')
            outfile.write('<TABLE CLASS="apilist">\n')
            for v in range(len(file_info.formInfoList)):
                fi = file_info.formInfoList[v]
                jdoc = fi.javadoc
                outfile.write(' <TR><TH COLSPAN="3">' + fi.name + '</TH></TR>\n')
                outfile.write(' <TR><TD COLSPAN="3">')
                if jdoc.isDefault():
                    outfile.write('<DIV CLASS="jd_desc">' + fi.title + '</DIV>')
                else:
                    if len(jdoc.desc)<1 or (len(jdoc.desc)==1 and jdoc.desc[0]==''): jdoc.desc.append(fi.title)
                    outfile.write( jdoc.getHtml(file_info.anchorNames[fi.uniqueNumber][0]) )
                outfile.write('  <DL><DT>'+_('Statistics')+':</DT><DD><TABLE CLASS="stat"><TR CLASS="tr0"><TD>' \
                    + _('XML Size') + '</TD><TD ALIGN="right">' + size_format(file_info.xmlbytes) + '</TD></TR><TR CLASS="tr1"><TD>' \
                    + _('PL/SQL Code') + '</TD><TD ALIGN="right">' + size_format(file_info.xmlcodebytes) + '<BR>(' + num_format(100*file_info.xmlcodebytes/file_info.xmlbytes,1) + '%)</TD></TR><TR CLASS="tr0"><TD>' \
                    + _('Packages') + '</TD><TD ALIGN="right">' + `len(fi.packageInfoList)` + '</TD></TR><TR CLASS="tr1"><TD>' \
                    + _('Functions') + '</TD><TD ALIGN="right">' + `len(fi.functionInfoList)` + '</TD></TR><TR CLASS="tr0"><TD>' \
                    + _('Procedures') + '</TD><TD ALIGN="right">' + `len(fi.procedureInfoList)` + '</TD></TR><TR CLASS="tr1"><TD>' \
                    + _('Triggers') + '</TD><TD ALIGN="right">' + `len(fi.triggerInfoList)` + '</TD></TR>')
                i = 0
                for s in fi.stats.keys():
                    if fi.stats[s]>0:
                        outfile.write('<TR CLASS="tr'+`i%2`+'"><TD>'+s+'</TD><TD ALIGN="right">'+`fi.stats[s]`+'</TD></TR>')
                        i += 1
                outfile.write('</TABLE></DD></TD></TR>\n')
                # Check form for packages
                if len(fi.packageInfoList) > 0:
                    packagedetails += '<A NAME="formpkgs"></A><H2>'+_('Form Packages')+'</H2>\n'
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Packages')+'</TH></TR>\n')
                    i = 0
                    detailCount = 0
                    for item in fi.packageInfoList:
                        html = ''
                        haveDetails = False
                        if not item.javadoc.isDefault(): haveDetails = True
                        ObjectDetailsListItem(item,i,fi.codesize,file_info)
                        html += '<A NAME="'
                        html += (item.javadoc.name or item.name.lower())
                        html += '_'+`item.uniqueNumber`+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom: 10px;" WIDTH="95%">\n'
                        html += ' <TR><TH>'
                        html += (item.javadoc.name or item.name)
                        html += '</TH></TR>\n <TR><TD>'
                        html += item.javadoc.getHtml(file_info.anchorNames[item.uniqueNumber][0])
                        html += '</TD></TR>\n'
                        i += 1
                        # check package for functions ###TODO: See above, they must be detected first
                        if len(item.functionInfoList) > 0:
                            fhtml = ''
                            for fu in item.functionInfoList:
                                if not fu.javadoc.isDefault(): fhtml += (formPkgFuncDetails(fu) or '')
                            if fhtml != '':
                                html += ' <TR><TD HEIGHT="0.5em"></TH></TR>\n'
                                html += ' <TR><TH CLASS="sub" STYLE="margin-top:0.5em;">'+_('Functions')+'</TH></TR>\n' + fhtml
                                haveDetails = True
                        # check package for procedures
                        if len(item.procedureInfoList) > 0:
                            fhtml = ''
                            for fu in item.procedureInfoList:
                                if not fu.javadoc.isDefault():
                                  fhtml += (formPkgFuncDetails(fu) or '')
                            if fhtml != '':
                                html += ' <TR><TD HEIGHT="0.5em"></TH></TR>\n'
                                html += ' <TR><TH CLASS="sub">'+_('Procedures')+'</TH></TR>\n' + fhtml
                                haveDetails = True
                        html += '</TABLE>\n'
                        if haveDetails:
                            packagedetails += html
                            detailCount += 1
                    if detailCount == 0: packagedetails += '<P ALIGN="center">'+_('No JavaDoc information available')+'</P>'
                # Check form for functions
                if len(fi.functionInfoList) > 0:
                    packagedetails += '<A NAME="formfuncs"></A><H2>'+_('Form Functions')+'</H2>\n'
                    outfile.write(' <TR><TD HEIGHT="0.5em" COLSPAN="3"></TH></TR>\n')
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Functions')+'</TH></TR>\n')
                    i = 0
                    html = ''
                    for item in fi.functionInfoList:
                        ObjectDetailsListItem(item,i,fi.codesize,file_info)
                        html += item.javadoc.getHtml(file_info.anchorNames[item.uniqueNumber][0])
                        i += 1
                    if html == '': packagedetails += '<P ALIGN="center">'+_('No JavaDoc information available')+'</P>'
                    else: packagedetails += html
                # Check form for procedures
                if len(fi.procedureInfoList) > 0:
                    packagedetails += '<A NAME="formprocs"></A><H2>'+_('Form Procedures')+'</H2>\n'
                    outfile.write(' <TR><TD HEIGHT="0.5em" COLSPAN="3"></TH></TR>\n')
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Procedures')+'</TH></TR>\n')
                    i = 0
                    html = ''
                    for item in fi.procedureInfoList:
                        ObjectDetailsListItem(item,i,fi.codesize,file_info)
                        html += item.javadoc.getHtml(file_info.anchorNames[item.uniqueNumber][0])
                        i += 1
                    if html == '': packagedetails += '<P ALIGN="center">'+_('No JavaDoc information available')+'</P>'
                    else: packagedetails += html
                outfile.write('</TABLE>\n');


        # Do we have packages in this file?
        if len(file_info.packageInfoList) > 0:
            outfile.write('<H2 CLASS="api">'+_('Package Overview')+'</H2>\n')
            outfile.write('<TABLE CLASS="apilist">\n')
            for p in range(len(file_info.packageInfoList)):
                jdoc = file_info.packageInfoList[p].javadoc
                aname = '<A NAME="'+file_info.packageInfoList[p].javadoc.name + '_' + `file_info.packageInfoList[p].uniqueNumber`+'"></A>'
                outfile.write(' <TR><TH COLSPAN="3">' + aname + file_info.packageInfoList[p].name + '</TH></TR>\n')
                outfile.write(' <TR><TD COLSPAN="3">')
                outfile.write( jdoc.getHtml(file_info.anchorNames[file_info.packageInfoList[p].uniqueNumber][0]) )
                outfile.write('</TD></TR>\n')
                # Check the packages for functions
                if len(file_info.packageInfoList[p].functionInfoList) > 0:
                    packagedetails += '<A NAME="funcs"></A><H2>'+_('Functions')+'</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Functions')+'</TH></TR>\n')
                    i = 0
                    for item in file_info.packageInfoList[p].functionInfoList:
                        ObjectDetailsListItem(item,i,file_info.bytes,file_info)
                        packagedetails += item.javadoc.getHtml(file_info.anchorNames[item.uniqueNumber][0])
                        i += 1
                # Check the packages for procedures
                if len(file_info.packageInfoList[p].procedureInfoList) > 0:
                    packagedetails += '<A NAME="procs"></A><H2>'+_('Procedures')+'</H2>\n';
                    outfile.write(' <TR><TH CLASS="sub" COLSPAN="3">'+_('Procedures')+'</TH></TR>\n')
                    i = 0
                    for item in file_info.packageInfoList[p].procedureInfoList:
                        ObjectDetailsListItem(item,i,file_info.bytes,file_info)
                        packagedetails += item.javadoc.getHtml(file_info.anchorNames[item.uniqueNumber][0])
                        i += 1
            outfile.write('</TABLE>\n\n')

        outfile.write(packagedetails)
        # ===[ JAVADOC END ]===

        # include the source itself
        if file_info.fileType == 'xml': codesize = file_info.formInfoList[0].codesize
        else: codesize = file_info.bytes
        if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or codesize <= metaInfo.includeSourceLimit ):
            outfile.write('\n<H2>'+_('Source')+'</H2>\n')
            outfile.write('<CODE><PRE>')
            if metaInfo.useCache:
                if cache.check(file_info.fileName,'code'):
                    code = cache.get(file_info.fileName,'code')
                else:
                    code = hypercode(readCodeFromFile(file_info), sqlkeywords, sqltypes)
                    cache.put(file_info.fileName, 'code', code)
            else:
                code = hypercode(readCodeFromFile(file_info), sqlkeywords, sqltypes)
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
                                href  = u[0].getHtmlName() + '#L' + repr(u[1])
                                patt = re.compile('\\b('+opname+')\\.('+oname+')\\b',re.I)
                                oricode = code
                                code = patt.sub('\\1.<A HREF="'+href+'">\\2</A>',code)
                                if code==oricode and file_info.fileName==u[0].fileName: # no match on full name
                                    patt = re.compile('\\b('+oname+')(\\s*\\()')
                                    code = patt.sub('<A HREF="'+href+'">\\1</A>\\2',code)
            try:
                if len(metaInfo.encoding)>8 and metaInfo.encoding[0:8].lower()=='iso-8859':
                    # though \xa4 should be '&curren;', it usually is '&euro;'. u'\xa4' does not translate to iso-8859-*
                    # Other characters are messed up by the Oracle Form converter already beyond repair possibility.
                    outfile.write( code.replace(u'\xa4','&euro;') )
                else:
                    outfile.write( code )
            except UnicodeEncodeError, detail:
                logger.error(_('Encoding trouble writing sourcecode of %s:'), file_info.fileName)
                logger.error(detail)
            outfile.write('</PRE></CODE>\n')
            outfile.write('<DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV><BR>\n')

        outfile.write(MakeHTMLFooter(file_info.fileName[len(top_level_directory)+1:]))
        outfile.close()

    # complete line on task completion
    pbarClose()


#------------------------------------------------------------------------------
def CreateWhereUsedPages():
    """Generate a where-used-page for each object"""

    from hypercore.helpers import CaseInsensitiveComparison

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
            html  = '<H1>' + _('Where Used List for %s') % tname +'</H1>\n'
        else:
            html  = '<H1>' + _('What Used List for %s') % tname +'</H1>\n'
        html += '<TABLE CLASS="apilist">\n'
        html += '  <TR><TH>'+_('Object')+'</TH><TH>'+_('File')+'</TH><TH>'+_('Line')+'</TH></TR>\n'
        return html

    def makeUsageColumn(filename,utuple,trclass=''):
        """
        Create the usage table
        @param string filename name of the file the usage was found in
        @param tuple utuple usage tuple
        @return string html usage table
        """
        if trclass!='': trclass = ' CLASS="'+trclass+'"'
        filename_short = filename[len(metaInfo.topLevelDirectory)+1:]
        line_number = utuple[1]
        unique_number = utuple[0].uniqueNumber
        html_file = fileMap[filename].getHtmlName()
        utype = utuple[2]
        uObj = utuple[3]
        if utype in ['func','proc'] and type(uObj.parent).__name__=='PackageInfo': uname = uObj.parent.name + '.'
        else: uname = ''
        if utype=='file': uname = filename[len(metaInfo.topLevelDirectory)+1:]
        elif uObj.javadoc.isDefault(): uname += uObj.name.lower()
        else: uname += uObj.javadoc.name
        if utype in ['func','proc']: uname += '()'
        if utype=='func'  : utype = 'function'
        elif utype=='proc': utype = 'procedure'
        elif utype=='pkg' : utype = 'package'

        html = '  <TR'+trclass+'><TD>' + utype + ' '

        # only make hypertext references for SQL files for now
        if utuple[0].fileType in ['sql','xml']:
            if utuple[0].fileType == 'xml':
                html += '<A HREF="' + html_file + '#' + utuple[0].anchorNames[uObj.uniqueNumber][0] + '">' + uObj.name + '</A></TD><TD>'
                codesize = utuple[0].formInfoList[0].codesize
            elif not metaInfo.useJavaDoc or uObj.javadoc.isDefault():
                html += uname + '</TD><TD>'
                codesize = utuple[0].bytes
            else:
                html += '<A HREF="' + html_file + '#' + utuple[0].anchorNames[uObj.uniqueNumber][0] + '">' + uname + '</A></TD><TD>'
                codesize = utuple[0].bytes
            if metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or codesize <= metaInfo.includeSourceLimit ):
                html += '<A HREF="' + html_file + '">' + filename_short + '</A></TD><TD ALIGN="right">'
                html += '<A href="' + html_file + '#L' + `line_number` + '">' + `line_number` + '</A>'
        else:
            html += uname + '</TD><TD>' + filename_short + '</TD><TD ALIGN="right">' + `line_number`

        html += '</TD></TR>\n'
        return html

    def makeUsagePage(page,otype,obj):
        """
        Write the where/what used page
        @param string page 'where' or 'what'
        @param string otype object type ('view','pkg','func','proc')
        @param object obj object info (object of type ElemInfo, see hypercore.py)
        """
        unum = obj.uniqueNumber
        if page=='where':
            used_keys = obj.whereUsed.keys()
            used_list = obj.whereUsed
            pname = _('Where Used List for %s') % obj.name
            fname = metaInfo.htmlDir + 'where_used_' + `unum` + '.html'
        else:
            used_keys = obj.whatUsed.keys()
            used_list = obj.whatUsed
            pname = _('What Used List for %s') % obj.name
            fname = metaInfo.htmlDir + 'what_used_' + `unum` + '.html'
        outfile = fopen(fname, 'w', metaInfo.encoding)
        if otype=='tab':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('Table'),obj.name,page) )
        elif otype=='view':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('View'),obj.name,page) )
        elif otype=='mview':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('Materialized View'),obj.name,page) )
        elif otype=='synonym':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('Synonym'),obj.name,page) )
        elif otype=='sequence':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('Sequence'),obj.name,page) )
        elif otype=='trigger':
            outfile.write(MakeHTMLHeader(pname))
            outfile.write( makeUsageTableHead(_('Trigger'),obj.name,page) )
        elif otype=='pkg':
            outfile.write(MakeHTMLHeader(obj.name + ' ' + pname))
            outfile.write( makeUsageTableHead(_('Package'),obj.name,page) )
        elif type(obj.parent).__name__=='PackageInfo':
            if otype=='func':
                outfile.write(MakeHTMLHeader(obj.name.lower() + ' '+_('from package')+' ' + obj.parent.name))
                outfile.write( makeUsageTableHead(_('Function'),obj.name.lower() + ' <I>'+_('from package')+' ' + obj.parent.name + ' </I>', page) )
            elif otype=='proc':
                outfile.write(MakeHTMLHeader(obj.name.lower() + ' '+_('from package')+' ' + obj.parent.name))
                outfile.write( makeUsageTableHead(_('Procedure'),obj.name.lower() + ' <I>'+_('from package')+' ' + obj.parent.name + ' </I>', page) )
        elif otype=='func':
            outfile.write(MakeHTMLHeader(obj.name.lower()))
            outfile.write( makeUsageTableHead(_('Function'),obj.name.lower(), page) )
        elif otype=='proc':
            outfile.write(MakeHTMLHeader(obj.name.lower()))
            outfile.write( makeUsageTableHead(_('Procedure'),obj.name.lower(), page) )
        elif otype=='form':
            outfile.write(MakeHTMLHeader(obj.name + ' ' + pname))
            outfile.write( makeUsageTableHead(_('Form'),obj.name,page) )
        else:
            logger.warn(_('makeUsagePage called for undefined type "%s"'),otype)
        used_keys.sort(CaseInsensitiveComparison)
        k = 0;
        for key in used_keys:
            for usedtuple in used_list[key]:
                outfile.write( makeUsageColumn(key,usedtuple,'tr'+`k % 2`) )
                k += 1
        outfile.write('</TABLE>')
        outfile.write(MakeHTMLFooter(pname))
        outfile.close()

    def makeWhat(obj,otype):
        if len(obj.whatUsed.keys()) != 0:
            makeUsagePage('what',otype,obj)
    def makeWhere(obj,otype):
        if len(obj.whereUsed.keys()) != 0:
            makeUsagePage('where',otype,obj)

    pbarInit(_('Creating "where used" pages'),0,len(metaInfo.fileInfoList), logname)

    # We need to map this in order to retrieve the corresponding html file names
    fileMap = {}
    for file_info in metaInfo.fileInfoList: fileMap[file_info.fileName] = file_info

    # loop through files
    i = 0
    for file_info in metaInfo.fileInfoList:

        # Update progressbar
        i += 1
        pbarUpdate(i)

        # skip all non-sql files
        if file_info.fileType not in ['sql','xml']:
            continue

        # loop through tables
        for tab_info in file_info.tabInfoList: makeWhere(tab_info,'tab')

        # loop through views
        for view_info in file_info.viewInfoList:
            makeWhere(view_info,'view')
            makeWhat(view_info,'view')

        # loop through mviews
        for view_info in file_info.mviewInfoList:
            makeWhere(view_info,'mview')
            makeWhat(view_info,'mview')

        # loop through synonyms
        for syn_info in file_info.synInfoList:
            makeWhere(syn_info,'synonym')

        # loop through sequences
        for seq_info in file_info.seqInfoList:
            makeWhere(seq_info,'sequence')
            makeWhat(seq_info,'sequence')

        # loop through triggers
        for trigger_info in file_info.triggerInfoList:
            makeWhat(trigger_info,'trigger')

        # loop through stand-alone functions
        for func_info in file_info.functionInfoList:
            makeWhere(func_info,'func')
            makeWhat(func_info,'func')

        # loop through standAlone procedures
        for proc_info in file_info.procedureInfoList:
            makeWhere(proc_info,'proc')
            makeWhat(proc_info,'proc')

        # loop through packages
        for package_info in file_info.packageInfoList:
            makeWhere(package_info,'pkg')
            makeWhat(package_info,'pkg')

            #look for any of this packages' functions
            for function_info in package_info.functionInfoList:
                makeWhere(function_info,'func')
                makeWhat(function_info,'func')

            #look for any of this packages procedures
            for procedure_info in package_info.procedureInfoList:
                makeWhere(procedure_info,'proc')
                makeWhat(procedure_info,'proc')

        # loop through forms
        for form_info in file_info.formInfoList:
            # no where_used pages here, so we go straight for the what_used
            makeWhat(form_info,'form')
            ###TODO:
            # check for form packages
            # check for form functions
            # check for form procedures

    # complete line on task completion
    pbarClose()


#==============================================================[ UnitTests ]===
#------------------------------------------------------------------------------
def CreateUnitTests():
    """
    Check the code for embedded testcases and generate the XML files for
    Unit Test generators input
    """

    if not metaInfo.unittests: return
    printProgress(_('Extracting Unit-Tests'), logname)

    from hypercore import unittest

    def processObject(otype,oInfo):
        """
        Process one object (i.e. function/procedure) and create the OBJECT XML element
        @param string otype object type. This must be either 'function' or 'procedure'
        @param object oInfo the function/procedure object from the list
        @return string xml SIGNATURE and TESTCASE blocks glued together (or empty string if no testcases)
        """
        otype = otype.lower()
        if otype not in ['function','procedure']:
            logger.warn(_('Object type %(otype)s is not supported for unit-tests, skipping "%(oname)s"'),{'otype':otype,'oname':(oInfo.javadoc.name or oInfo.name)})
            return ''
        xml = ''
        for tc in oInfo.javadoc.testcase:
            xml += unittest.testcase(tc)
        if xml != '':
            params = []
            for param in oInfo.javadoc.params: params.append({'name':param.name,'type':param.inout,'datatype':param.sqltype}) ###TODO: Optional params
            if len(oInfo.javadoc.retVals)>0: retval = oInfo.javadoc.retVals[0].sqltype
            else: retval = None
            sig = unittest.signature(oInfo.javadoc.name,params,retval)
            xml = unittest.xobject(otype,oInfo.name,sig,xml)
        return xml

    # Walk the input files. We generate one XML per input file if the latter contains testcases
    for file_info in metaInfo.fileInfoList:

        so_test   = ''
        testsuite = ''
        fname     = os.path.split(file_info.fileName)[1].replace(".", "_")

        for fi in file_info.functionInfoList:   # check stand-alone functions
            so_test += processObject('function',fi)
        for fi in file_info.procedureInfoList:  # check stand-alone procedures
            so_test += processObject('procedure',fi)
        if so_test != '': # we have testcases for stand-alone stuff - they need their separate testsuite
            testsuite = unittest.testsuite('standalone',fname,so_test)
        for pi in file_info.packageInfoList:    # check packages
            pkgtest = ''
            for fi in pi.functionInfoList:      # check package functions
                pkgtest += processObject('function',fi)
            for fi in pi.procedureInfoList:     # check package procedures
                pkgtest += processObject('procedure',fi)
            if pkgtest != '': # we need a dedicated testsuit per package
                testsuite += unittest.testsuite('package',(pi.javadoc.name or pi.name),pkgtest)

        if testsuite != '':                     # only create XML if we have testcases
            xmlfile = os.path.join( metaInfo.unittest_dir, fname ) + '.xml'
            outfile = fopen(xmlfile, 'w', metaInfo.encoding)
            outfile.write('<?xml version="1.0" encoding="'+metaInfo.encoding+'"?>\n')
            outfile.write( unittest.unittest(testsuite) )
            outfile.close()

