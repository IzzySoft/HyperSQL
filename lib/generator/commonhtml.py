"""
Common HTML stuff
"""
__revision__ = '$Id$'

import time # for makeHTMLFooter
from os import path as os_path # for getDualCodeLink, purge_html, CreateIndexPage, MakeFileIndex, CreateDepGraphIndex
from os import listdir,unlink  # for purge_html
from hypercore.elements import metaInfo
from progress import *
from iz_tools.system import fopen

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
logger = logg.getLogger('GenHTML')

#=====================================================[ directory handling ]===
#------------------------------------------------------------------------------
def CreateDirectories():
    """Creates the output directories if needed"""
    printProgress(_("Creating output subdirectories"), logname)
    from iz_tools.system import makeRDir

    makeRDir(metaInfo.htmlDir)                              # make sure the HTML output dir exists
    if metaInfo.unittests: makeRDir(metaInfo.unittest_dir)  # same for UnitTest XML output


#------------------------------------------------------------------------------
def purge_html():
    """
    Cleanup files left in the HTML output directory left from the previous run(s)
    """
    purge = False
    if metaInfo.cmdOpts.purgeHTML is None:
        if metaInfo.config.getBool('Process','purge_on_start',False): purge = True
    else:
        if metaInfo.cmdOpts.purgeHTML: purge = True
    if purge:
        printProgress(_("Removing files generated by previous run"), logname)
        if os_path.exists(metaInfo.htmlDir):
            names=listdir(metaInfo.htmlDir)
            for i in names:
                unlink(os_path.join(metaInfo.htmlDir,i))
        if metaInfo.unittests and os_path.exists(metaInfo.unittest_dir):
            names=listdir(metaInfo.unittest_dir)
            for i in names:
                if os_path.splitext(i)[1]=='.xml': unlink(os_path.join(metaInfo.unittest_dir,i))


#------------------------------------------------------------------------------
def CleanRemovedFromCache():
    """
    Check the cache for copies of already deleted/moved files
    """
    if metaInfo.useCache:
        printProgress(_('Checking cache for copies of already deleted/moved files'), logname)
        import hypercore.cache
        cache = hypercore.cache.cache(metaInfo.cacheDirectory)
        dc    = cache.removeObsolete(metaInfo.topLevelDirectory)
        logger.info(_('%s obsolete files removed from cache'), dc)


#------------------------------------------------------------------------------
def purge_cache():
    if metaInfo.cmdOpts.purge_cache is not None:
        cache = hypercore.cache.cache(metaInfo.cacheDirectory)
        for name in metaInfo.cmdOpts.purge_cache: cache.clear(name)
    CleanRemovedFromCache()


#------------------------------------------------------------------------------
def CopyStaticFiles():
    """Copy static files (CSS etc.) to HTML dir"""
    printProgress(_('Copying static files'), logname)

    from shutil import copy2

    # Copy the StyleSheet
    if os_path.exists(metaInfo.css_file):
      try:
        copy2(metaInfo.css_file,os_path.join(metaInfo.htmlDir,os_path.split(metaInfo.css_file)[1]))
      except IOError:
        logger.error(_('I/O error while copying %(source)s to %(target)s'), {'source':_('CSS-File'),'target':_('HTML-Dir')})
    for css in metaInfo.custom_css_files:
      if os_path.exists(css):
        try:
          copy2(css,os_path.join(metaInfo.htmlDir,os_path.split(css)[1]))
        except IOError:
          logger.error(_('I/O error while copying %(source)s to %(target)s'), {'source':_('CSS-File')+' '+css,'target':_('HTML-Dir')})

    # Copy project logo (if any)
    if metaInfo.projectLogo != '':
      try:
        copy2(metaInfo.projectLogo,os_path.join(metaInfo.htmlDir,os_path.split(metaInfo.projectLogo)[1]))
      except IOError:
        logger.error(_('I/O error while copying %(source)s to %(target)s'), {'source':_('project logo'),'target':_('HTML-Dir')})


#================================================================[ helpers ]===
#------------------------------------------------------------------------------
def MakeNavBar(current_page):
    """
    Generates HTML code for the general navigation links to all the index pages
    The current page will be handled separately (no link, highlight)
    @param string current_page name of the current page
    """
    itemCount = 0
    s = "<TABLE CLASS='topbar' WIDTH='98%'><TR>\n"
    s += "  <TD CLASS='navbar'>\n"
    elems_per_row = metaInfo.navbar_elems_per_row
    for item in metaInfo.pages:
        if metaInfo.indexPage[item] == '':
            continue
        if current_page == item:
            s += '    <SPAN CLASS="active_element">' + metaInfo.indexPageName[item] + '</SPAN> &nbsp;&nbsp; \n'
        else:
            s += '    <A HREF="' + metaInfo.indexPage[item] + '">' + metaInfo.indexPageName[item] + '</A> &nbsp;&nbsp; \n'
        itemCount += 1
        if ( elems_per_row > 0 and itemCount % elems_per_row == 0 ):
            s += '    <BR>\n'
    if current_page == 'Index':
        s += '    <SPAN CLASS="active_element">'+_('Main Index')+'</SPAN>\n'
    else:
        s += '    <A HREF="index.html">'+_('Main Index')+'</A>\n'
    s += "  </TD><TD CLASS='title'>\n"
    s += '    ' + metaInfo.title_prefix + '\n'
    s += '  </TD>\n'
    s += '</TR></TABLE>\n'
    return s


#------------------------------------------------------------------------------
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
    s += '<HTML><HEAD>\n'
    s += '  <TITLE>' + metaInfo.title_prefix + ': ' + title_text + '</TITLE>\n'
    s += '  <LINK REL="stylesheet" TYPE="text/css" HREF="' + metaInfo.css_file + '">\n'
    for css in metaInfo.custom_css_files:
        s += '  <LINK REL="stylesheet" TYPE="text/css" HREF="' + os_path.split(css)[1] + '">\n'
    s += '  <META HTTP-EQUIV="Content-Type" CONTENT="text/html;charset='+metaInfo.encoding+'">\n'
    if charts:
        s += '  <SCRIPT Language="JavaScript" src="diagram.js" TYPE="text/javascript"></SCRIPT>\n'
    if onload=='':
        s += '</HEAD><BODY>\n'
    else:
        s += '</HEAD><BODY ONLOAD="'+onload+'">\n'
    s += '<A NAME="topOfPage"></A>\n'
    s += MakeNavBar(title_name)
    s += '<HR CLASS="topend">\n'
    return s


#------------------------------------------------------------------------------
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
    s += "</BODY></HTML>"
    return s


#------------------------------------------------------------------------------
def getDualCodeLink(otuple):
    """
    Calculates links to Code and JavaDoc ref and returns them as HTMLref,HTMLjref,HTMLpref,HTMLpjref
    @param tuple otuple object-tuple (name,object,fileInfo,packageInfo)
    @return string HTMLref link to code
    @return string HTMLjref link to JavaDoc reference
    @return string HTMLpref link to package code
    @return string HTMLpjref link to JavaDoc package reference
    """
    # HTML[j]ref links to function Code / [ApiDoc]
    HTMLref = otuple[2].getHtmlName()
    if otuple[1].javadoc.isDefault():
        HTMLjref = ''
    else:
        try:
            HTMLjref = HTMLref + '#' + otuple[2].anchorNames[otuple[1].uniqueNumber][0]
        except KeyError:
            logger.error('*** KEYERROR FOR ANCHOR OF "'+otuple[0]+'" ***')
            logger.error(otuple[1])
    # HTMLp[j]ref links to package Code [ApiDoc]
    if len(otuple) > 3 and otuple[3]: # otuple[3] is package_info
        if otuple[3].javadoc.isDefault():
            HTMLpjref = ''
        else:
            HTMLpjref = HTMLref + '#' + otuple[2].anchorNames[otuple[3].uniqueNumber][0]
        HTMLpref = HTMLref + "#L" + str(otuple[3].lineNumber)
    else:
        HTMLpjref = ''
        HTMLpref  = ''
    HTMLref += "#L" + str(otuple[1].lineNumber)
    return HTMLref,HTMLjref,HTMLpref,HTMLpjref


#------------------------------------------------------------------------------
def makeDualCodeRef(href,jref,name,tsize):
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
        if href[0]!='' and metaInfo.includeSource and ( metaInfo.includeSourceLimit==0 or tsize <= metaInfo.includeSourceLimit ):
            anchor += ' <SUP><A HREF="'+href+'">#</A></SUP>'
    else:
        if href[0]=='' or not metaInfo.includeSource or ( metaInfo.includeSourceLimit>0 and tsize > metaInfo.includeSourceLimit ):
            anchor = name
        else:
            anchor = '<A HREF="'+href+'">'+name+'</A>'
    return anchor


#------------------------------------------------------------------------------
def makeUsageCol(where,what,unum,tdatt='',manused=False,manuses=False):
    """
    Create a table column with usage references.
    This is a helper to several procedures creating element pages.
    @param boolean where do we have where_used?
    @param boolean what do we have what_used?
    @param int unum uniqueNumber for filename
    @param optional string tdatt additional table attributes
    @param optional boolean manused usage marked manually using @used
    @param optional boolean manuses usage marked manually using @uses
    @return string html
    """
    s = '<TD CLASS="whereused"'+tdatt+'>'
    if where:
        ref = 'where_used_%d.html' % unum
        s += '<A href="' + ref + '">'+_('where used')+'</A> / '
    elif manused: s += '@ / '
    elif what or manuses: s += '- / '
    else: s += _("no use found")
    if what:
        ref = 'what_used_%d.html' % unum
        s += '<A href="' + ref + '">'+_('what used')+'</A>'
    elif manuses: s += '@'
    elif where or manused: s += '-'
    s += '</TD>'
    return s


#=============================================================[ generators ]===
#------------------------------------------------------------------------------
def CreateIndexPage():
    """Generates the main index page"""
    printProgress(_('Creating site index page'), logname)

    from iz_tools.system import fopen

    outfile = fopen(os_path.join(metaInfo.htmlDir,'index.html'), 'w', metaInfo.encoding)
    outfile.write(MakeHTMLHeader('Index'))

    outfile.write('<H1 ID="infotitle">' + metaInfo.title_prefix + ' '+_('HyperSQL Reference')+'</H1>\n')

    outfile.write('<BR><BR>\n')
    outfile.write('<TABLE ID="projectinfo" ALIGN="center"><TR><TD VALIGN="middle" ALIGN="center">\n')
    if metaInfo.projectLogo != '':
      logoname = os_path.split(metaInfo.projectLogo)[1]
      outfile.write('  <IMG ALIGN="center" SRC="' + logoname + '" ALT="Logo"><BR><BR><BR>\n')
    outfile.write(metaInfo.projectInfo)
    outfile.write('</TD></TR></TABLE>\n')
    outfile.write('<BR><BR>\n')

    outfile.write(MakeHTMLFooter('Index'))
    outfile.close()


#------------------------------------------------------------------------------
def MakeFileIndex(objectType):
    """
    Generate HTML index page for all files, ordered by
    path names (filepath) or file names (file)
    @param string objectType either 'file' or 'filepath'
    @param string html_title main heading (H1) for the generated content
    @param object outfile file object to write() to
    """

    if objectType not in ['file','filepath']: # unsupported type
        return
    if metaInfo.indexPage[objectType] == '':  # this index is disabled
        return

    outfile = fopen(os_path.join(metaInfo.htmlDir,metaInfo.indexPage[objectType]), "w", metaInfo.encoding)
    outfile.write(MakeHTMLHeader(objectType))

    if objectType == 'file':
        printProgress(_("Creating filename no path index"), logname)
        html_title = _('Index Of All Files By File Name')
    else:
        printProgress(_("Creating filename by path index"), logname)
        html_title = _('Index Of All Files By Path Name')

    filenametuplelist = []
    for file_info in metaInfo.fileInfoList:
        # skip all non-sql files
        if file_info.fileType != "sql":
            continue
        if objectType == 'file':
            filenametuplelist.append((os_path.split(file_info.fileName)[1].upper(), file_info))
        else:
            filenametuplelist.append((file_info.fileName.upper(), file_info))
    filenametuplelist.sort(key=lambda x: x[0])

    outfile.write("<H1>"+html_title+"</H1>\n")
    outfile.write("<TABLE CLASS='apilist'>\n")
    i = 0

    for filenametuple in filenametuplelist:
        file_name = filenametuple[1].fileName
        temp = filenametuple[1].getHtmlName()
        if objectType == 'file':
            outfile.write("  <TR CLASS='tr%d'><TD><A href=\"" % (i % 2) + temp + "\">" + os_path.split(file_name)[1])
        else:
            outfile.write("  <TR CLASS='tr%d'><TD><A href=\"" % (i % 2) + temp + "\">" + file_name[len(metaInfo.topLevelDirectory)+1:])
        outfile.write("</A></TD></TR>\n")
        i += 1

    outfile.write("</TABLE>\n")

    outfile.write(MakeHTMLFooter(objectType))
    outfile.close()


#------------------------------------------------------------------------------
def CreateDepGraphIndex():
    """ Generate the depgraphs and their index page """

    from depgraph import depgraph
    from shutil import copy2
    if metaInfo.useCache: import hypercore.cache

    if metaInfo.indexPage['depgraph']=='':
        return

    g = depgraph(metaInfo.graphvizMod, metaInfo.encoding, metaInfo.depGraphDelTmp)
    if not g.deps_ok: # we cannot do anything
        logger.error(_('Graphviz trouble - unable to generate the graph'))
        return

    i = 0
    pbarInit(_('Creating dependency graphs'), i, metaInfo.depGraphCount, logname)

    g.set_fontname(metaInfo.fontName)
    g.set_fontsize(metaInfo.fontSize)
    g.set_ranksep(metaInfo.graphRankSepDot,'dot')
    g.set_ranksep(metaInfo.graphRankSepTwopi,'twopi')
    g.set_ranksep(metaInfo.graphLenFdp,'fdp')
    g.set_ranksep(metaInfo.graphLenNeato,'neato')
    g.set_ranksep(metaInfo.graphDistCirco,'circo')

    if metaInfo.useCache: cache = hypercore.cache.cache(metaInfo.cacheDirectory)

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
                        try:
                          copy2(os_path.join(metaInfo.cacheDirectory,gname), os_path.join(metaInfo.htmlDir,gname))
                          done = True
                        except:
                          logger.error(_('Error while copying %s from cache'), gname)
                if not done:
                    g.set_graph(metaInfo.depGraph[gtyp])
                    res = g.make_graph(metaInfo.htmlDir + gname)
                    if res=='':
                        if metaInfo.useCache:
                          try:
                            cache.put(gtyp,'depdata','\n'.join(metaInfo.depGraph[gtyp]))
                            copy2(os_path.join(metaInfo.htmlDir,gname), os_path.join(metaInfo.cacheDirectory,gname))
                          except:
                            logger.error(_('Error while copying %s to cache'), gname)
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

    outfile = fopen(os_path.join(metaInfo.htmlDir,metaInfo.indexPage['depgraph']), "w", metaInfo.encoding)
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



