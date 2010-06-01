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
            mview = 'MViewIndex.html',
            tab = 'TableIndex.html',
            trigger = 'TriggerIndex.html',
            synonym = 'SynonymIndex.html',
            sequence = 'SequenceIndex.html',
            package = 'PackageIndex.html',
            package_full = 'PackagesWithFuncsAndProcsIndex.html',
            function = 'FunctionIndex.html',
            procedure = 'ProcedureIndex.html',
            form = 'FormIndex.html',
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
            mview = _('Materialized View Index'),
            tab = _('Table Index'),
            trigger = _('Trigger Index'),
            synonym = _('Synonym Index'),
            sequence = _('Sequence Index'),
            package = _('Package Index'),
            package_full = _('Full Package Listing'),
            function = _('Function Index'),
            procedure = _('Procedure Index'),
            form = _('Form Index'),
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
            mview = '0',
            tab = '0',
            trigger = '0',
            synonym = '0',
            sequence = '0',
            package = '1',
            package_full = '1',
            function = '1',
            procedure = '1',
            form = '0',
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
            whereused_scan_instring = '0',
            cache = '1',
            link_code_calls = '1'
        )
        # Section LOGGING
        logg = dict (
            screenlevel = 'ERROR',
            filelevel = 'DEBUG',
            logfile = 'HyperSQL.log',
            progress = '1',
            verification = '0'
        )
        # Section VERIFICATION
        verification = dict (
            javadoc_mandatory = '0',
            verify_javadoc = '0',
            author_in_report = '0',
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
            objects  = 'view pkg proc func synonym',
            file2file = '1',
            file2object = '0',
            object2file = '1',
            object2object = '1',
            deltmp = '1',
        )
        # Section COLORS
        colors = dict (
            pkg = '#0000ff #ffffff',
            proc = '#3366ff #ffffff',
            func = '#66aaff #000000',
            tab = '#774411 #ffffff',
            trigger = '#33ffff #000000',
            mview = '#bb6611 #ffffff',
            view = '#eeaa55 #000000',
            synonym = '#00ff00 #000000',
            sequence = '#ffcc00 #000000',
            typ = '#ffff33 #000000',
            form = '#993366 #ffffff',
            bug = '#ff0000 #ffffff',
            warn = '#eeaa55 #000000',
            todo = '#3366ff #ffffff',
            code = '#0000ff #ffffff',
            comment = '#bb6611 #ffffff',
            mixed = '#eeaa55 #000000',
            empty = '#dddddd #000000',
            file = '#dddddd #000000',
            filebig = '#ff0000 #ffffff',
            file100k = '#ff4422 #ffffff',
            file50k = '#dd9944 #000000',
            file25k = '#ffcc00 #000000',
            file10k = '#00ff00 #000000',
            file1000l = '#0000ff #ffffff',
            file400l = '#ffcc00 #000000'
        )
        # Section FORMS
        forms = dict (
            pck_mark = 'Package Body',
            pcks_mark = 'Package-Spez.',
            proc_mark = 'Prozedur',
            func_mark = 'Funktion'
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
        vals['Colors']    = colors
        vals['Forms']     = forms
        self.setVals( vals )
