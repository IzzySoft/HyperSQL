"""
$Id$
HyperSQL Command Line Options
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from optparse import OptionParser, OptionGroup
from .gettext_init import langpath, langs
import gettext

gettext.bindtextdomain('hyperopts', langpath)
gettext.textdomain('hyperopts')
lang = gettext.translation('hyperopts', langpath, languages=langs, fallback=True)
_ = lang.ugettext

class hyperopts(object):
    """
    HyperSQL command line parser.
    Makes use of Pythons optparse module
    """
    def __init__(self,progname=None,ver=None):
        """
        Initialize the class and setup OptionParser
        @param self
        @param optional string progname name of the program (default: argv[0])
        """
        self.parser = OptionParser(usage=_('Syntax: %prog [options] [project]'),description=_('Options can be used to override configured values.'),version=ver,prog=progname)
        self.optAdd()
        (self.options, self.args) = self.parser.parse_args()

    def optAdd(self):
        """ add our options """
        self.parser.add_option('-c','--config',dest='config',help=_('config file to use'))
        self.parser.add_option('-i','--input',dest='sourceDir',help=_('directory to parse for source files'))
        self.parser.add_option('-o','--output',dest='htmlDir',help=_('directory the generated HTML files should be written to'))
        # Cache handling options
        cache = OptionGroup(self.parser,_('Cache Options'))
        cache.add_option('--cache',dest='cache',action='store_true',help=_('turn the cache on'))
        cache.add_option('--nocache',dest='cache',action='store_false',help=_('turn the cache off'))
        cache.add_option('--cache-dir',dest='cacheDir',help=_('override the cache dir location'))
        cache.add_option('--purge-cache',dest='purge_cache',choices=['all','code','depdata'],action='append', \
            help=_('purge the specified cache at the very start. Possible values are: all, code, depdata. Multiple definitions are possible.'))
        self.parser.add_option_group(cache)
        # Processing options
        proc = OptionGroup(self.parser,_('Processing Options'))
        proc.add_option('--blind-offset',type='int',dest='blind_offset',help=_('set the "blind offset" to this number of lines'))
        proc.add_option('--javadoc',dest='javadoc',action='store_true',help=_('process javadoc'))
        proc.add_option('--nojavadoc',dest='javadoc',action='store_false',help=_('do not process javadoc'))
        proc.add_option('--link-calls',dest='linkCalls',action='store_true',help=_('link to targets in code calls'))
        proc.add_option('--nolink-calls',dest='linkCalls',action='store_false',help=_('do not link to targets in code calls'))
        proc.add_option('-p','--page',dest='pages',action='append',help=_('process this page. Multiple definitions (for multiple pages) are possible.'))
        proc.add_option('-P','--nopage',dest='nopages',action='append',help=_('do not process this page. Multiple definitions (for multiple pages) are possible.'))
        proc.add_option('--purge-html',dest='purgeHTML',action='store_true',help=_('purge old HTML files before creating the new ones'))
        proc.add_option('--nopurge-html',dest='purgeHTML',action='store_false',help=_('do not purge old HTML files before creating the new ones'))
        proc.add_option('--scan-instring',dest='scanInString',action='store_true',help=_('scan in strings for where/what objects are used'))
        proc.add_option('--noscan-instring',dest='scanInString',action='store_false',help=_('do not scan in strings for where/what objects are used'))
        proc.add_option('--scan-shortrefs',dest='scanShortrefs',action='store_true',help=_('scan short references for where/what objects are used'))
        proc.add_option('--noscan-shortrefs',dest='scanShortrefs',action='store_false',help=_('do not scan short references for where/what objects are used'))
        proc.add_option('--source',dest='source',action='store_true',help=_('include (and link to) highlighted source'))
        proc.add_option('--nosource',dest='source',action='store_false',help=_('do not include (and link to) highlighted source'))
        proc.add_option('--verify-javadoc',dest='verifyJavadoc',action='store_true',help=_('check for Javadoc errors and write the corresponding report'))
        proc.add_option('--noverify-javadoc',dest='verifyJavadoc',action='store_false',help=_('do not check for Javadoc errors and do not write the corresponding report'))
        self.parser.add_option_group(proc)
        # Logging related options
        log = OptionGroup(self.parser,_('Logging Options'))
        log.add_option('--cron',dest='cron',action='store_true',help=_('suppress all non-error output to STDOUT. This is equivalent to --noprogress --screen-loglevel ERROR and, as the name suggests, intended to be used for automated runs via a scheduler'))
        log.add_option('--file-loglevel',dest='fileLogLevel',choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL','NONE'],help=_('log level to use for the log file'))
        log.add_option('--logfile',dest='logfile',help=_('use the specified file to write our log into'))
        log.add_option('--progress',dest='progress',action='store_true',help=_('write progress information to STDOUT'))
        log.add_option('--noprogress',dest='progress',action='store_false',help=_('do not write progress information to STDOUT'))
        log.add_option('-q','--quiet',dest='bequiet',action='store_true',help=_('suppress all output to STDOUT. This is equivalent to --noprogress --screen-loglevel NONE'))
        log.add_option('--screen-loglevel',dest='screenLogLevel',choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL','NONE'],help=_('log level to use for STDOUT'))
        log.add_option('--verification-log',dest='verificationLog',action='store_true',help=_('log javadoc verification messages'))
        log.add_option('--noverification-log',dest='verificationLog',action='store_false',help=_('do not log javadoc verification messages'))
        self.parser.add_option_group(log)
        # Dependency graphs
        dep = OptionGroup(self.parser,_('Dependency Graph Options'))
        dep.add_option('--graph',dest='graph',choices=['file2file','file2object','object2file','object2object'],action='append',help=_('draw the specified graph (multiple definitions allowed)'))
        dep.add_option('--nograph',dest='nograph',choices=['file2file','file2object','object2file','object2object'],action='append',help=_('do not draw the specified graph (multiple definitions allowed)'))
        dep.add_option('--graphviz-font',dest='graphvizFont',help=_('name of the font to use for the graphs (e.g. Arial)'))
        dep.add_option('--graphviz-fontsize',dest='graphvizFontSize',type='float',help=_('size of the font to use for the graphs (e.g. 10 or 8.5)'))
        dep.add_option('--depobjects',dest='depObjects',choices=['view','pkg','func','proc'],action='append',help=_('objects to include with the dependency graphs. Multiple specifications (one per required object) are possible.'))
        dep.add_option('--graphviz-processor',dest='graphvizProc',choices=['dot','fdp','neato','circo'],help=_('which graphviz module to use'))
        dep.add_option('--len-fdp',dest='len_fdp',type='float',help=_('len parameter for the fdp processor'))
        dep.add_option('--len-neato',dest='len_neato',type='float',help=_('len parameter for the neato processor'))
        dep.add_option('--mindist-circo',dest='mindist_circo',type='float',help=_('mindist parameter for the circo processor'))
        dep.add_option('--ranksep-dot',dest='ranksep_dot',type='float',help=_('space between the levels (for the dot processor)'))
        dep.add_option('--ranksep-twopi',dest='ranksep_twopi',type='float',help=_('space between the levels (for the twopi processor)'))
        self.parser.add_option_group(dep)

    def getOpts(self):
        """
        Obtain all options
        @return object options { object.name = value}
        """
        return self.options

    def getArgs(self):
        """
        Obtain all non-option positional arguments
        (those following the options on the command line)
        @return list params
        """
        return self.args
        
    def setVer(self,version):
        self.parser.version = version

"""
opts = hyperopts(ver='1.2.3')
print opts.getOpts()
print opts.getArgs()
"""
