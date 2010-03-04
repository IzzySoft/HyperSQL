"""
$Id$
HyperSQL Configuration Class
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from IniParser import IniParser

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
        @param defaults A dictionary of intrinsic defaults. The keys must be
               strings, the values must be appropriate for %()s string
               interpolation.  Note that `__name__' is always an intrinsic
               default; it's value is the section's name.
        """
        IniParser.__init__(self,defaults)

    def initDefaults(self):
        """
        Initialize configuration with HyperSQL default settings
        """
        # Section GENERAL
        general = dict(
            title_prefix='HyperSQL',
            project_info='This is my HyperSQL project.',
            project_info_file='',
            project_logo='',
            project_logo_url='',
            bugzilla_url='',
            wiki_url='',
            encoding='utf8'
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
            todo = 'TodoIndex.html'
        )
        # Section PAGENAMES
        pagenames = dict (
            file = 'File Name Index',
            filepath = 'File Names by Path Index',
            view = 'View Index',
            package = 'Package Index',
            package_full = 'Full Package Listing',
            function = 'Function Index',
            procedure = 'Procedure Index',
            bug = 'Bug List',
            todo = 'Todo List'
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
        )
        # Section PROCESS
        process = dict (
            purge_on_start = '0',
            blind_offset = '0',
            include_source = '1',
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
        # Generate the final dict (dict() allows no nesting)
        vals = {}
        vals['General']   = general
        vals['FileNames'] = filenames
        vals['PageNames'] = pagenames
        vals['Pages']     = pages
        vals['Process']   = process
        vals['Logging']   = logg
        self.setVals( vals )
