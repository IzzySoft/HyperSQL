#!/usr/bin/env python
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
__revision__ = '$Id$'
__version__  = '3.8.7'


# first import standard modules we use
import os, sys, re, gettext

# now import our own modules
sys.path.insert(0,os.path.split(sys.argv[0])[0] + os.sep + 'lib')
from hypercore.logger import logg
from hypercore.elements import *
from hypercore.helpers import *
from hypercore.javadoc import *
from hypercore.config import *
from hypercore.config import _ # needs explicit call
from hypercore.charts import *
from iz_tools.system import *
from depgraph import *
from hypercore.options import hyperopts
from generator.commonhtml import *
from generator.db_html import *
from generator.sqlstats import MakeStatsPage
import hypercore.cache
import parser.sqlfinder


#------------------------------------------------------------------------------
def FindFilesAndBuildFileList(sdir, fileInfoList, init=True):
    """
    Recursively scans the source directory specified for relevant files according
    to the file extensions configured in metaInfo, while excluding RCS
    directories (see rcsnames in configuration section FileNames). Information
    for matching files is stored in fileInfoList.
    @param string sdir directory to scan
    @param list fileInfoList where to store results
    """
    from parser.filefinder import getFileList
    printProgress(_("Creating file list"), logName)

    # setup wanted file extensions
    fileExts = [('sql',metaInfo.sql_file_exts),('cpp',metaInfo.cpp_file_exts)]
    if metaInfo.indexPage['form'] != '': fileExts.append(('xml',['xml']))

    # retrieve the list
    fileInfoList += getFileList(sdir,fileExts,metaInfo.rcsnames)
    cpos  = len(sdir)
    if sdir[cpos-1] != os.sep: cpos += 1

    # some adjustments are required
    for f in fileInfoList:
        f.uniqueName = f.fileName[cpos:].replace('.','_').replace('/','--') # unique Name (for new-style refs)
        if f.uniqueNumber == 0: f.uniqueNumber = metaInfo.NextIndex()       # unique Number (old style, deprecated)


#------------------------------------------------------------------------------
def confPage(page):
    """
    Add the specified page to the list of pages to process if it is enabled
    @param string page index key for the page to setup
    @param string filenameDefault default for the file name (used if not found in config)
    @param string pagenameDefault default for the page name (used if not found in config)
    @param boolean enableDefault
    """
    if page in metaInfo.cmdOpts.nopages and page not in metaInfo.cmdOpts.pages:
        metaInfo.indexPage[page] = ''
    elif page in metaInfo.cmdOpts.pages and page not in metaInfo.cmdOpts.nopages or config.getBool('Pages',page,True):
        metaInfo.indexPage[page] = config.get('FileNames',page)
        metaInfo.indexPageName[page] = config.get('PageNames',page)
        metaInfo.indexPageCount += 1
    else:
        metaInfo.indexPage[page] = ''


#------------------------------------------------------------------------------
def confColors(name,bg,fg):
    """
    Configure color tuples for Graphs
    @param string name name of the tuple
    @param string bg foreground color (Hex HTML color value, e.g. '#ffffff')
    @param string fg text color (Hex HTML color value, e.g. '#ffffff')
    """
    mask = r'#[A-f0-9]{6}'
    cvals = config.getList('Colors',name)
    if cvals and re.match(mask,cvals[0]) and re.match(mask,cvals[1]):
        metaInfo.colors[name] = cvals
    else:
        metaInfo.colors[name] = [bg,fg]


#------------------------------------------------------------------------------
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
    metaInfo.topLevelDirectory  = metaInfo.cmdOpts.sourceDir or config.get('FileNames','top_level_directory','.') # directory under which all files will be scanned
    JavaDocVars['top_level_dir_len'] = len(metaInfo.topLevelDirectory)
    metaInfo.rcsnames           = config.getList('FileNames','rcsnames',['RCS','CVS','.svn']) # directories to ignore
    metaInfo.sql_file_exts      = config.getList('FileNames','sql_file_exts',['sql', 'pkg', 'pkb', 'pks', 'pls']) # Extensions for files to treat as SQL
    metaInfo.cpp_file_exts      = config.getList('FileNames','cpp_file_exts',['c', 'cpp', 'h']) # Extensions for files to treat as C
    if len(metaInfo.cmdArgs)>0: defCacheDir = os.path.split(sys.argv[0])[0] + os.sep + "cache" + os.sep + metaInfo.cmdArgs[0] + os.sep
    else: defCacheDir = os.path.split(sys.argv[0])[0] + os.sep + "cache" + os.sep
    metaInfo.cacheDirectory     = metaInfo.cmdOpts.cacheDir or config.get('FileNames','cache_dir',defCacheDir)
    if metaInfo.cmdOpts.cache is None: metaInfo.useCache = config.getBool('Process','cache',True)
    else: metaInfo.useCache = metaInfo.cmdOpts.cache
    metaInfo.htmlDir            = metaInfo.cmdOpts.htmlDir or config.get('FileNames','htmlDir',os.path.split(sys.argv[0])[0] + os.sep + "html" + os.sep)
    metaInfo.css_file           = config.get('FileNames','css_file','hypersql.css')
    metaInfo.css_url            = config.get('FileNames','css_url','')
    metaInfo.unittest_dir       = config.get('FileNames','unittest_dir',os.path.split(sys.argv[0])[0] + os.sep + "unittests" + os.sep)
    metaInfo.indexPageCount     = 1 # We at least have the main index page
    if metaInfo.cmdOpts.pages is None:   metaInfo.cmdOpts.pages = []
    if metaInfo.cmdOpts.nopages is None: metaInfo.cmdOpts.nopages = []
    # order of metaInfo.pages defines the order of the navbar!
    metaInfo.pages = ['package','package_full','function','procedure','tab','view','mview','synonym','sequence','type','trigger','form','form_full','file','filepath','bug','todo','report','stat','depgraph']
    for page in metaInfo.pages:
        confPage(page)
    # Sections PAGES and PAGENAMES are handled indirectly via confPage() in section FileNames
    # Section PROCESS
    if metaInfo.cmdOpts.blind_offset is None:
        metaInfo.blindOffset = abs(config.getInt('Process','blind_offset',0)) # we need a positive integer
    else:
        metaInfo.blindOffset = abs(metaInfo.cmdOpts.blind_offset)
    if metaInfo.cmdOpts.source is None:
        metaInfo.includeSource = config.getBool('Process','include_source',True)
    else: metaInfo.includeSource = metaInfo.cmdOpts.source
    metaInfo.includeSourceLimit = config.getInt('Process','include_source_limit',0)*1024
    if metaInfo.cmdOpts.javadoc is None:
        metaInfo.useJavaDoc = config.getBool('Process','javadoc',True)
    else: metaInfo.useJavaDoc = metaInfo.cmdOpts.javadoc
    if metaInfo.useJavaDoc: metaInfo.unittests = config.getBool('Process','export_unittests',False)
    else: metaInfo.unittests = False
    if metaInfo.cmdOpts.linkCalls is None:
        metaInfo.linkCodeCalls = config.getBool('Process','link_code_calls',True)
    else: metaInfo.linkCodeCalls = metaInfo.cmdOpts.linkCalls
    if metaInfo.cmdOpts.scanShortrefs is None:
        metaInfo.scanShortRefs = config.getBool('Process','whereused_scan_shortrefs')
    else: metaInfo.scanShortRefs = metaInfo.cmdOpts.scanShortrefs
    if metaInfo.cmdOpts.scanInString is None:
        metaInfo.scanInString = config.getBool('Process','whereused_scan_instring')
    else:
        metaInfo.scanInString = metaInfo.cmdOpts.scanInString
    # Section VERIFICATION
    JavaDocVars['javadoc_mandatory'] = config.getBool('Verification','javadoc_mandatory',False)
    if metaInfo.cmdOpts.verifyJavadoc is None:
        JavaDocVars['verification'] = config.getBool('Verification','verify_javadoc',False)
    else: JavaDocVars['verification'] = metaInfo.cmdOpts.verifyJavadoc
    JavaDocVars['author_in_report'] = config.getBool('Verification','author_in_report',False)
    JavaDocVars['mandatory_tags'] = config.getList('Verification','mandatory_tags',[])
    JavaDocVars['form_stats'] = config.getBool('Verification','stats_javadoc_forms',False)
    JavaDocVars['verify_forms'] = config.getBool('Verification','verify_forms',False)
    # Section DEPGRAPH
    metaInfo.graphvizMod   = metaInfo.cmdOpts.graphvizProc or config.get('DepGraph','processor','fdp')
    metaInfo.fontName      = metaInfo.cmdOpts.graphvizFont or config.get('DepGraph','fontname','')
    metaInfo.fontSize      = metaInfo.cmdOpts.graphvizFontSize or config.get('DepGraph','fontsize','')
    metaInfo.graphRankSepDot  = metaInfo.cmdOpts.ranksep_dot or config.get('DepGraph','ranksep_dot','')
    metaInfo.graphRankSepTwopi  = metaInfo.cmdOpts.ranksep_twopi or config.get('DepGraph','ranksep_twopi','')
    metaInfo.graphLenNeato = metaInfo.cmdOpts.len_neato or config.get('DepGraph','len_neato','')
    metaInfo.graphLenFdp = metaInfo.cmdOpts.len_fdp or config.get('DepGraph','len_fdp','')
    metaInfo.graphDistCirco = metaInfo.cmdOpts.mindist_circo or config.get('DepGraph','mindist_circo','')
    metaInfo.depGraphObjects = metaInfo.cmdOpts.depObjects or config.getList('DepGraph','objects',['view','pkg','proc','func'])
    metaInfo.makeDepGraph = {}
    metaInfo.makeDepGraph['file2file']     = config.getBool('DepGraph','file2file',True)
    metaInfo.makeDepGraph['file2object']   = config.getBool('DepGraph','file2object',False)
    metaInfo.makeDepGraph['object2file']   = config.getBool('DepGraph','object2file',True)
    metaInfo.makeDepGraph['object2object'] = config.getBool('DepGraph','object2object',True)
    if metaInfo.cmdOpts.graph is not None:
        for name in metaInfo.cmdOpts.graph:
            if metaInfo.cmdOpts.nograph is None or name not in metaInfo.cmdOpts.nograph:
                metaInfo.makeDepGraph[name] = True
    if metaInfo.cmdOpts.nograph is not None:
        for name in metaInfo.cmdOpts.nograph:
            if metaInfo.cmdOpts.graph is None or name not in metaInfo.cmdOpts.graph:
                metaInfo.makeDepGraph[name] = False
    metaInfo.depGraphCount = 0
    if metaInfo.makeDepGraph['file2file']:     metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['file2object']:   metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['object2file']:   metaInfo.depGraphCount += 1
    if metaInfo.makeDepGraph['object2object']: metaInfo.depGraphCount += 1
    metaInfo.depGraphDelTmp = config.getBool('DepGraph','deltmp',True)
    # Section LOGGING
    if metaInfo.cmdOpts.progress is None:
        metaInfo.printProgress = config.getBool('Logging','progress',True)
    else: metaInfo.printProgress = metaInfo.cmdOpts.progress
    if metaInfo.cmdOpts.verificationLog is None:
        JavaDocVars['verification_log'] = config.getBool('Logging','verification',False)
    else:
        JavaDocVars['verification_log'] = metaInfo.cmdOpts.verificationLog
    # Section COLORS
    confColors('pkg', '#0000ff','#ffffff')
    confColors('proc', '#3366ff','#ffffff')
    confColors('func', '#66aaff','#000000')
    confColors('trigger', '#33ffff','#000000')
    confColors('form','#0066cc','#ffffff')
    confColors('tab', '#774411','#ffffff')
    confColors('view', '#eeaa55','#000000')
    confColors('mview', '#bb6611','#ffffff')
    confColors('synonym', '#00ff00','#000000')
    confColors('sequence', '#ffcc00', '#000000')
    confColors('typ', '#ffff33','#000000')
    confColors('file', '#dddddd','#000000')
    confColors('empty', '#dddddd','#000000')
    confColors('code', '#0000ff','#ffffff')
    confColors('comment', '#bb6611','#ffffff')
    confColors('mixed', '#eeaa55','#000000')
    confColors('bug', '#ff0000','#ffffff')
    confColors('warn', '#eeaa55','#000000')
    confColors('todo', '#3366ff','#ffffff')
    confColors('filebig', '#ff0000','#ffffff')
    confColors('file100k', '#ff4422','#ffffff')
    confColors('file50k', '#eeaa55','#000000')
    confColors('file25k', '#ffcc00','#000000')
    confColors('file10k', '#00ff00','#000000')
    confColors('file1000l', '#0000ff','#ffffff')
    confColors('file400l', '#ffcc00','#000000')
    # JavaDoc types for SQL
    JavaDocVars['otypes'] = {
              'function':  dict(name='function',  otags=['param','return','throws']),
              'procedure': dict(name='procedure', otags=['param','throws']),
              'table':     dict(name='table',     otags=['col']),
              'view':      dict(name='view',      otags=['col']),
              'mview':     dict(name='mview',     otags=['col']),
              'trigger':   dict(name='trigger',   otags=[]),
              'synonym':   dict(name='synonym',   otags=[]),
              'sequence':  dict(name='sequence',  otags=[]),
              'pkg':       dict(name='package',   otags=[]),
              'form':      dict(name='form',      otags=[]),
              'type':      dict(name='type',      otags=[])
    } # supported object types
    JavaDocVars['supertypes'] = ['pkg','form'] # object types with subobjects


#------------------------------------------------------------------------------
def confDeps():
    """ Check dependent options and fix them, if necessary """
    if metaInfo.indexPage['depgraph']!='':
        dg = depgraph()
        if not dg.deps_ok: metaInfo.indexPage['depgraph'] = ''
    if metaInfo.cmdOpts.cron:
        metaInfo.cmdOpts.screenLogLevel = 'ERROR'
        metaInfo.printProgress = False
    #elif metaInfo.cmdOpts.quiet:
    elif metaInfo.cmdOpts.cache:
        metaInfo.cmdOpts.screenLogLevel = 'NONE'
        metaInfo.printProgress = False


#------------------------------------------------------------------------------
def confLogger():
    """ Setup logging """
    fname = metaInfo.cmdOpts.logfile or config.get('Logging','logfile')
    maxbytes = config.getInt('Logging','maxkbytes',0) * 1024 # rotate at x kB
    backupCount = config.getInt('Logging','backupcount',3)
    captureWarnings = config.get('Logging','capture_warnings',False)
    fileLevel = metaInfo.cmdOpts.fileLogLevel or config.get('Logging','filelevel','WARNING')
    screenLevel = metaInfo.cmdOpts.screenLogLevel or config.get('Logging','screenlevel','WARNING')

    logg.setScreenLog(screenLevel)
    logg.setFileLog(fileLevel,fname,metaInfo.encoding,maxbytes,backupCount)


#==============================================================================
if __name__ == "__main__":

    metaInfo.versionString = __version__
    metaInfo.scriptName = sys.argv[0]
    logName = os.path.splitext(os.path.basename(metaInfo.scriptName))[0]

    # Option parser
    opts = hyperopts(progname=os.path.split(metaInfo.scriptName)[1],ver=metaInfo.versionString)
    metaInfo.cmdOpts = opts.getOpts()
    metaInfo.cmdArgs = opts.getArgs()

    # Read configuration
    config = HyperConf()
    config.initDefaults()

    # Check the config files
    confName = []
    if metaInfo.cmdOpts.config is not None:
        if os.path.exists(metaInfo.cmdOpts.config): confName.append(metaInfo.cmdOpts.config)
        else: print 'specified config file %s not found' % metaInfo.cmdOpts.config
    if len(confName)==0:
        metaInfo.scriptpath = os.path.split(sys.argv[0])[0]
        for proj in ['HyperSQL','hypersql']:
            pfile = os.path.join(metaInfo.scriptpath, proj) + '.ini'
            if not pfile in confName and os.path.exists(pfile):
                confName.append(pfile)
        if len(metaInfo.cmdArgs)>0:
            for proj in [metaInfo.cmdArgs[0].lower(),metaInfo.cmdArgs[0]]:
                pfile = os.path.join(metaInfo.scriptpath, proj) + '.ini'
                if not pfile in confName and os.path.exists(pfile):
                    confName.append(pfile)
    # If we have any config files, read them!
    if len(confName) > 0:
      config.read(confName)
    elif not metaInfo.cmdOpts.quiet and not metaInfo.cmdOpts.cron and (metaInfo.cmdOpts.progress is None or metaInfo.cmdOpts.progress):
      print _('No config file found, using defaults.')

    configRead()
    confDeps()

    # Initiate logging
    if metaInfo.printProgress: from progress import *
    confLogger()
    from hypercore.logger import logg
    logger = logg.getLogger()
    printProgress(_('HyperSQL v%s initialized') % metaInfo.versionString, logName)
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

    metaInfo.config = config

    from generator.sqlstats import MakeStatsPage

    # ----------------
    # Start processing
    # ----------------

    purge_cache()
    FindFilesAndBuildFileList(metaInfo.topLevelDirectory, metaInfo.fileInfoList)
    parser.sqlfinder.ScanFilesForObjects()
    parser.sqlfinder.ScanFilesForUsage()

    purge_html()

    CreateDirectories()
    CopyStaticFiles()

    # Generating the index pages
    CreateIndexPage()
    MakeFileIndex('filepath')
    MakeFileIndex('file')
    MakeElemIndex('tab')
    MakeElemIndex('view')
    MakeElemIndex('mview')
    MakeElemIndex('synonym')
    MakeElemIndex('sequence')
    MakeElemIndex('trigger')
    MakeElemIndex('type')
    MakePackageIndex()
    MakePackagesWithFuncsAndProcsIndex()
    MakeMethodIndex('function')
    MakeMethodIndex('procedure')
    MakeFormIndex()
    MakeFormIndexWithUnits()

    # Bug and Todo lists
    MakeTaskList('bug')
    MakeTaskList('todo')
    MakeTaskList('report')
    MakeStatsPage()

    # Dependencies
    CreateWhereUsedPages()
    CreateDepGraphIndex()

    # Details
    CreateHyperlinkedSourceFilePages()
    CreateUnitTests()

    logger.info('Processed %s total lines: %s empty, %s plain comments, %s plain code, %s mixed', \
        metaInfo.getLoc('totals'), metaInfo.getLoc('empty'), metaInfo.getLoc('comment'), metaInfo.getLoc('code'), \
        metaInfo.getLoc('totals') - metaInfo.getLoc('empty') - metaInfo.getLoc('comment') - metaInfo.getLoc('code'))
    logger.info('Percentage: %s%% empty, %s%% plain comments, %s%% plain code, %s%% mixed', \
        metaInfo.getLocPct('empty'), metaInfo.getLocPct('comment'), metaInfo.getLocPct('code'), \
        metaInfo.getLocPct('mixed'))
    printProgress(_('HyperSQL v%s exiting normally') % metaInfo.versionString +'\n', logName)
