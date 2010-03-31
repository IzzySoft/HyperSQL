"""
$Id$
HyperSQL Configuration Class
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from IniParser import IniParser
from locale import getdefaultlocale
from os import environ, path as ospath, sep as ossep
from sys import argv as sysargv
import gettext

# Setup gettext
langs = []
lc, encoding = getdefaultlocale()
if (lc):
    langs = [lc,lc[:2]]
language = environ.get('LANGUAGE', None)
if (language):
    langs += language.split(":")
langs += ['en_US']
langpath = ospath.split(sysargv[0])[0] + ossep + 'lang'
gettext.bindtextdomain('hypersql', langpath)
gettext.textdomain('hypersql')
lang = gettext.translation('hypersql', langpath, languages=langs, fallback=True)
_ = lang.ugettext



class HyperConf(IniParser):
    """
    An extension to ConfigParser, mainly adding a Default parameter to
    option retrieval - plus a getList method.
    As for the defaults which may be passed to ConfigParser.__init__,
    they cannot be assigned to a specific section - so if the same keyword
    exists in multiple sections, those defaults are useless. That's why
    HyperConf allows to pass defaults to the get methods.
    """
    def __init__(self,defaults=None):
        """
        Initialize the instance
        @param self
        @param defaults A dictionary of intrinsic defaults. The keys must be
               strings, the values must be appropriate for %()s string
               interpolation.  Note that `__name__' is always an intrinsic
               default; it's value is the section's name. These defaults are
               not section specific.
        """
        IniParser.__init__(self,defaults)

    def initDefaults(self):
        """
        Initialize configuration with HyperSQL default settings
        @param self
        """
        # Section GENERAL
        general = dict(
            title_prefix='HyperSQL',
            project_info='This is my HyperSQL project.',
            project_info_file='',
            project_logo='',
            project_logo_url='',
            ticket_url='',
            wiki_url='',
            encoding='utf8',
        )
        # Section FILENAMES
        filenames = dict (
            top_level_directory = '.',
            rcsnames = 'RCS CVS .svn',
            sql_file_exts = 'sql pks pkb pkg pls',
            cpp_file_exts = 'c cpp h',
            htmldir = 'html/',
            css_file = 'hypersql.css',
            css_url = '',
            file = 'FileNameIndexNoPathnames.html',
            filepath = 'FileNameIndexWithPathnames.html',
            view = 'ViewIndex.html',
            package = 'PackageIndex.html',
            package_full = 'PackagesWithFuncsAndProcsIndex.html',
            function = 'FunctionIndex.html',
            procedure = 'ProcedureIndex.html',
            bug = 'BugIndex.html',
            todo = 'TodoIndex.html',
            report = 'ReportIndex.html',
            stat = 'StatIndex.html',
            depgraph = 'DepGraphIndex.html'
        )
        # Section PAGENAMES
        pagenames = dict (
            file = _('File Name Index'),
            filepath = _('File Names by Path Index'),
            view = _('View Index'),
            package = _('Package Index'),
            package_full = _('Full Package Listing'),
            function = _('Function Index'),
            procedure = _('Procedure Index'),
            bug = _('Bug List'),
            todo = _('Todo List'),
            report = _('Validation Report'),
            stat = _('Code Statistics'),
            depgraph = _('Dependency Graphs')
        )
        # Section PAGES
        pages = dict (
            file = '1',
            filepath = '1',
            view = '0',
            package = '1',
            package_full = '1',
            function = '1',
            procedure = '1',
            bug = '1',
            todo = '1',
            report = '0',
            stat = '0',
            depgraph = '1'
        )
        # Section PROCESS
        process = dict (
            purge_on_start = '0',
            blind_offset = '0',
            include_source = '1',
            javadoc = '1',
            whereused_scan_shortrefs = '0',
            whereused_scan_instring = '0'
        )
        # Section LOGGING
        logg = dict (
            screenlevel = 'ERROR',
            filelevel = 'DEBUG',
            logfile = 'HyperSQL.log',
            progress = '1'
        )
        # Section VERIFICATION
        verification = dict (
            javadoc_mandatory = '0',
            verify_javadoc = '0',
            mandatory_tags = ''
        )
        # Section DEPGRAPH
        depgraph = dict (
            processor = 'fdp',
            fontname = '',
            fontsize = '',
            ranksep_dot  = '',
            ranksep_twopi  = '',
            len_neato = '',
            len_fdp = '',
            mindist_circo = '',
            objects  = 'view pkg proc func',
            file2file = '1',
            file2object = '0',
            object2file = '1',
            object2object = '1',
            deltmp = '1'
        )
        # Generate the final dict (dict() allows no nesting)
        vals = {}
        vals['General']   = general
        vals['FileNames'] = filenames
        vals['PageNames'] = pagenames
        vals['Pages']     = pages
        vals['Process']   = process
        vals['Logging']   = logg
        vals['Verification'] = verification
        vals['DepGraph']  = depgraph
        self.setVals( vals )
