"""
HyperSQL Javadoc support
Copyright 2010 Itzchak Rehberg & IzzySoft
"""
__revision__ = '$Id$'

from .gettext_init import langpath, langs
from sys import maxint, argv as pargs
from .unittest import testcase_split
from iz_tools.typecheck import is_list, nullDict # for ScanJavaDoc, JavaDoc
import re, gettext, locale, os
from hypercore.logger import logg
logger = logg.getLogger('JavaDoc')

# Setup gettext support
gettext.bindtextdomain('hyperjdoc', langpath)
gettext.textdomain('hyperjdoc')
lang = gettext.translation('hyperjdoc', langpath, languages=langs, fallback=True)
_ = lang.ugettext

# Define some more settings
JavaDocVars = dict(
    wiki_url     = '',
    ticket_url = '',
    top_level_dir_len = 0,
    javadoc_shortdesc_mode = 'unit',
    javadoc_mandatory = False,
    javadoc_mandatory_objects = ['func','proc','pkg'],
    verification = False,
    verification_log = False,
    author_in_report = False,
    mandatory_tags = [],
    mandatory_code_tags = [],
    mandatory_codetag_objects = [],
    otypes = {}, # supported object types
    supertypes = [], # object types with subobjects
    tags   = ['param', 'return', 'version', 'author', 'info', 'example',
              'todo', 'bug', 'copyright', 'deprecated', 'private',
              'see', 'webpage', 'license', 'ticket', 'wiki', 'since',
              'uses', 'ignore','ignorevalidation', 'throws', 'col', 'used', 'verbatim', 'testcase'], # other supported tags
    txttags = ['version', 'author', 'info', 'example', 'todo', 'bug',
               'copyright', 'deprecated', 'see', 'webpage', 'license',
               'ticket', 'wiki', 'desc', 'since', 'uses', 'throws',
               'used', 'verbatim', 'testcase'] # values of these tags are plain text
)

def setJDocEncoding(encoding):
    """
    Switch encoding to a different character set
    @param string encoding
    """
    try:
        gettext.bind_textdomain_codeset('hyperjdoc',encoding.upper())
    except:
        pass


def HyperScan(text):
    """
    Search for URLS and make them clickable
    This includes not-yet-hyperlinked http:// elements, ticket: and wiki: references
    (the latter two depending on configuration of ticket_url and wiki_url)
    @param string text to scan
    """
    refpatt = re.compile("[^'\">](http\:\/\/\S+)+")    # URL-Regexp
    result = refpatt.search(text)
    while result != None:
        for g in range(len(result.groups())):
            text = text.replace(result.group(g) , ' <A HREF="'+result.group(g).strip()+'">'+result.group(g).strip()+'</A>')
        result = refpatt.search(text)
    if JavaDocVars['wiki_url'] != '':
        wikipat = re.compile("[^>](wiki:\S+)+")            # Wiki Page RegExp
        result = wikipat.search(text)
        while result != None:
            for g in range(len(result.groups())):
                text = text.replace(result.group(g) , ' <A HREF="'+JavaDocVars['wiki_url'].replace('%{page}',result.group(g).split(':')[1])+'">'+result.group(g).strip()+'</A>')
            result = refpatt.search(text)
    if JavaDocVars['ticket_url'] != '':
        tickpat = re.compile("[^>](ticket:\d+)+")              # Ticket RegExp
        result = tickpat.search(text)
        while result != None:
            for g in range(len(result.groups())):
                text = text.replace(result.group(g) , ' <A HREF="'+JavaDocVars['ticket_url'].replace('%{id}',result.group(g).split(':')[1])+'">'+result.group(g).strip()+'</A>')
            result = tickpat.search(text)
    return text

class JavaDoc(object):
    """
    Object to hold details from javadoc style comments
    """
    def __init__(self):
        """
        Initializes all properties with useful defaults.
        """
        self.file = ''
        self.lineNumber = -1
        self.lndiff = maxint # needed for function/procedure overloading
        self.lines = 0
        # tags extracted
        self.name = ''
        self.objectType = ''
        self.params = []
        self.retVals = []
        self.cols = []
        self.desc = []
        self.version = []
        self.author = []
        self.info = []
        self.example = []
        self.todo = []
        self.bug = []
        self.copyright = []
        self.deprecated = []
        self.private = False
        self.ignore = False
        self.ignorevalidation = False
        self.see = []
        self.webpage = []
        self.license = []
        self.ticket = []
        self.wiki = []
        self.since = []
        self.uses = []
        self.used = []
        self.throws = []
        self.verbatim = []
        self.testcase = []

    def __repr__(self):
        """ Basic information for simple debug """
        if self.isDefault(): return 'empty JavaDoc object'
        if self.objectType: ret = self.objectType
        else: ret = 'unknown object'
        if self.name: ret += ' ' + self.name
        if self.file:
            ret += ' from ' + self.file
            if self.lineNumber!=-1: ret += ' at line ' + str(self.lineNumber)
        return ret

    def log(self,msg):
        """
        Log a message
        @param self
        @param string msg what to log
        """
        if JavaDocVars['verification_log']: logger.info(msg)

    def isDefault(self):
        """
        Check if this is just an empty dummy, or if any real data have been assigned
        @param self
        @return boolean True (is a dummy) or False (has concrete data)
        """
        if self.lineNumber != -1: return False
        return True
    def verify_mandatory(self):
        """
        Verify the element according to configured parameters.
        @param self
        @return list
        """
        faillist = []
        if self.isDefault() or self.ignore or self.ignorevalidation or not JavaDocVars['verification']:
            return faillist
        if self.objectType in JavaDocVars['mandatory_codetag_objects']:
            checktags = JavaDocVars['mandatory_code_tags']
        else:
            checktags = JavaDocVars['mandatory_tags']
        for tag in checktags:
            if tag in JavaDocVars['txttags']:
                jdvar = self.__getattribute__(tag)
                if len(jdvar)==0 or (len(jdvar)==1 and len(jdvar[0])==0):
                    if tag == 'desc':
                        faillist.append(_('Missing description'))
                    else:
                        faillist.append(_('Missing mandatory tag: @%s') % tag)
                    self.log(_('Missing mandatory tag "%(tag)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'tag':tag, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        for param in self.params:
            if param.name == '':
                faillist.append(_('Missing name for %(type)s parameter (#%(index)s)') % {'type': param.sqltype, 'index': self.params.index(param)})
                self.log(_('Missing name for parameter of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':param.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
            if param.desc == '' and 'desc' in JavaDocVars['mandatory_tags']:
                if param.name == '':
                    faillist.append(_('Missing description for %(type)s parameter (#%(index)s)') % {'type':param.sqltype, 'index':self.params.index(param)})
                    self.log(_('Missing description for parameter of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':param.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
                else:
                    faillist.append(_('Missing description for parameter %s') % param.name)
                    self.log(_('Missing description for parameter "%(pname)s" for %(otype)s %(oname)s in %(file)s line %(line)s') % {'pname':param.name, 'otype':self.objectType, 'oname':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        for col in self.cols:
            if col.name == '':
                faillist.append(_('Missing name for %(type)s column (#%(index)s)') % {'type': col.sqltype, 'index': self.cols.index(col)})
                self.log(_('Missing name for column of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':col.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
            if col.desc == '' and 'desc' in JavaDocVars['mandatory_tags']:
                if col.name == '':
                    faillist.append(_('Missing description for %(type)s column (#%(index)s)') % {'type':col.sqltype, 'index':self.cols.index(col)})
                    self.log(_('Missing description for column of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':col.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
                else:
                    faillist.append(_('Missing description for column %s') % col.name)
                    self.log(_('Missing description for column "%(pname)s" for %(otype)s %(oname)s in %(file)s line %(line)s') % {'pname':col.name, 'otype':self.objectType, 'oname':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        if 'return' in JavaDocVars['otypes'][self.objectType]['otags'] and len(self.retVals)<1:
            faillist.append(_('Missing return value'))
            self.log(_('Missing return value for %(otype)s %(name)s in %(file)s line %(line)s') % {'otype':JavaDocVars['otypes'][self.objectType]['name'], 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        return faillist
    def verify_params(self,cparms):
        """
        Compare the parameters passed in code with those defined by JavaDoc comments
        @param self
        @param list cparms code parameters
        @return list
        """
        faillist = []
        if self.isDefault() or not JavaDocVars['verification']:
            return faillist
        if len(cparms) != len(self.params):
            faillist.append(_('Parameter count mismatch: Code has %(cparms)s parameters, Javadoc %(jparms)s') % { 'cparms':len(cparms), 'jparms':len(self.params)})
            self.log(_('Parameter count mismatch for %(otype)s %(name)s in %(file)s line %(line)s (%(lc)s / %(lj)s)') % {'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber, 'lc':len(cparms), 'lj':len(self.params)})
        return faillist
    def getVisibility(self):
        """
        Return the objects visibility ('private ', 'public ' or '')
        @param self
        @return string visibility ('private ', 'public ' or '')
        """
        if self.isDefault():
            return ''
        elif self.private:
            return 'private '
        else:
            return 'public '
    def getHtml(self,aname):
        """
        Generates HTML block from JavaDoc Api Info for the element passed - or
        an empty string if it is still the default empty element.
        @param self
        @param string aname anchor name for HTML anchor to this object (a name=xxx)
        @return string html code block
        """
        def listItemHtml(item):
            """
            If some txttag has multiple entries, we want an unordered list,
            otherwise just a simple line
            @param list item
            @return string html
            """
            entries = len(item)
            if entries < 1:
                return ''
            elif entries < 2:
                return item[0]
            else:
                txt = '<UL>'
                for i in range(entries):
                    txt += '<LI>'+item[i]+'</LI>'
                txt += '</UL>'
                return txt
        if self.isDefault() or self.ignore:
            return ''
        if self.objectType not in JavaDocVars['otypes']:
            if self.name == '':
                self.log(_('Unnamed object in %(file)s line %(line)s has no object type set!') % {'file':self.file, 'line':self.lineNumber})
            else:
                self.log(_('No object type specified for object id %(name)s in %(file)s line %(line)s') % {'name':self.name, 'file':self.file, 'line':self.lineNumber})
            return ''
        html = ''
        if self.objectType not in JavaDocVars['supertypes']:
          html = '<A NAME="'+aname+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom:10px" WIDTH="95%"><TR><TH>' + self.name + '</TH>\n'
          html += '<TR><TD>\n';
        if len(self.desc) > 0:
          html += '  <DIV CLASS="jd_desc">' + ' '.join(self.desc) + '</DIV>\n'
        html += '  <DL>'
        if self.private:
          html += ' <DT>'+_('Private')+'</DT><DD>'+_('Just used internally.')+'</DD>'

        if 'param' in JavaDocVars['otypes'][self.objectType]['otags']:
          html += '  <DT>'+_('Syntax')+':</DT><DD><DIV STYLE="margin-left:15px;text-indent:-15px;">' + self.name + ' ('
          for p in range(len(self.params)):
            html += self.params[p].name
            if p<len(self.params)-1:
              html += ', '
          html += ')</DIV></DD>\n'
          if len(self.params) > 0:
            html += ' <DT>'+_('Parameters')+':</DT><DD><TABLE><TR>'
            html += '<TH CLASS="sub">' + _('Parameter') + '</TH>'
            html += '<TH CLASS="sub">In/Out</TH>'
            html += '<TH CLASS="sub">' + _('Data Type') + '</TH>'
            html += '<TH CLASS="sub">' + _('Description') + '</TH></TR>'
            i = 0
            for p in range(len(self.params)):
              html += '<TR CLASS="tr'+str(i)+'"><TD>' + self.params[p].name + '</TD>'
              html += '<TD>' + self.params[p].inout + '</TD>'
              html += '<TD>' + self.params[p].sqltype + '</TD>'
              if self.params[p].desc != '': html += '<TD>' + self.params[p].desc + '</TD></TR>'
              else: html += '<TD>&nbsp;</TD></TR>'
              i = (i+1) % 2
            html += '</TABLE></DD>\n'

        if 'return' in JavaDocVars['otypes'][self.objectType]['otags']:
          html += ' <DT>'+_('Return values')+':</DT><DD><UL STYLE="list-style-type:none;margin-left:-40px;">'
          for p in range(len(self.retVals)):
            html += '<LI>' + self.retVals[p].sqltype + ' <B>' + self.retVals[p].name + '</B>'
            if self.retVals[p].desc != '':
              html += ': ' + self.retVals[p].desc
            html += '</LI>'
          html += '</UL></DD>\n'

        if 'col' in JavaDocVars['otypes'][self.objectType]['otags'] and len(self.cols)>0:
          html += ' <DT>'+_('Columns')+':</DT><DD><TABLE>'
          html += '<TR><TH CLASS="sub">'+_('Column')+'</TH><TH CLASS="sub">'
          html += _('Data Type')+'</TH><TH CLASS="sub">'+_('Description')+'</TH></TR>'
          i = 0
          for p in range(len(self.cols)):
            html += '<TR CLASS="tr'+str(i)+'"><TD>' + self.cols[p].name + '</TD>'
            html += '<TD>' + self.cols[p].sqltype + '</TD>'
            if self.cols[p].desc != '': html += '<TD>' + self.cols[p].desc + '</TD></TR>'
            else: html += '<TD>&nbsp;</TD></TR>'
            i = (i+1) % 2
          html += '</TABLE></DD>\n'

        if len(self.example) > 0:
          html += '<DT>'+_('Example Usage')+':</DT>'
          for i in range(len(self.example)):
            html += '<DD>' + self.example[i] + '</DD>'

        if len(self.testcase) > 0:
            html += '<DT>'+_('Unit-Tests')+':</DT><DD><TABLE>'
            for tcs in self.testcase:
                tc = testcase_split(tcs)
                html += '<TR><TH CLASS="delim" COLSPAN="2">&nbsp;</TH></TR>'
                html += '<TR><TH COLSPAN="2" CLASS="sub">'+(tc['name'] or _('NoName'))+'</TH></TR>'
                i = 0
                if tc['comment'] != '':
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Comment')+':&nbsp;</TD><TD>'+tc['comment']+'</TD></TR>'
                    i = (i+1) % 2
                if tc['message'] != '':
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Error Message')+':&nbsp;</TD><TD>'+tc['message']+'</TD></TR>'
                    i = (i+1) % 2
                basetypes = nullDict()
                for bt in tc['basetypes']: basetypes[bt['var']] = bt['val']
                if len(tc['params'])>0:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Parameters')+':&nbsp;</TD><TD><TABLE>'
                    html += '<TR><TD><B>'+_('Name')+'</B></TD><TD><B>'+_('Basetype')+'</B></TD><TD><B>'+_('Value')+'</B></TD></TR>'
                    for par in tc['params']: html += '<TR><TD>'+par['var']+'</TD><TD>'+(basetypes[par['var']] or '')+'</TD><TD>'+par['val']+'</TD></TR>'
                    html += '</TABLE></TD></TR>'
                    i = (i+1) % 2
                if len(tc['check'])>0:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Check OUT Parameters')+':&nbsp;</TD><TD><TABLE>'
                    html += '<TR><TD><B>'+_('Name')+'</B></TD><TD><B>'+_('Operator')+'</B></TD><TD><B>'+_('Value')+'</B></TD></TR>'
                    for par in tc['check']: html += '<TR><TD>'+par['var']+'</TD><TD ALIGN="center">'+par['op']+'</TD><TD>'+par['val']+'</TD></TR>'
                    html += '</TABLE></TD></TR>'
                    i = (i+1) % 2
                if tc['ret'] is not None:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Return values')+':&nbsp;</TD><TD>'+tc['ret']['op']+' '+tc['ret']['val']+'</TD></TR>'
                    i = (i+1) % 2
                if tc['presql']:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Testcase PreSQL')+':&nbsp;</TD><TD><PRE>'+tc['presql']+'</PRE></TD></TR>'
                    i = (i+1) % 2
                if tc['postsql']:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Testcase PostSQL')+':&nbsp;</TD><TD><PRE>'+tc['postsql']+'</PRE></TD></TR>'
                    i = (i+1) % 2
                if tc['checksql']:
                    html += '<TR CLASS="tr'+str(i)+'"><TD>'+_('Testcase CheckSQL')+':&nbsp;</TD><TD><PRE>'+tc['checksql']+'</PRE></TD></TR>'
            html += '</TABLE></DD>\n'

        if len(self.author) > 0:
          html += '<DT>'+_('Author')+':</DT><DD>' + listItemHtml(self.author) + '</DD>'
        if len(self.copyright) > 0:
          html += '<DT>'+_('Copyright')+':</DT><DD>' + listItemHtml(self.copyright) + '</DD>'
        if len(self.license) > 0:
          html += '<DT>'+_('License')+':</DT><DD>' + listItemHtml(self.license) + '</DD>'
        if len(self.webpage) > 0:
          html += '<DT>'+_('Webpage')+':</DT>'
          for i in range(len(self.webpage)):
            html += '<DD><A HREF="' + self.webpage[i] + '">' + self.webpage[i] + '</A></DD>'
        if len(self.since) > 0:
          html += '<DT>'+_('Available Since')+':</DT><DD>' + HyperScan(listItemHtml(self.since)) + '</DD>'
        if len(self.uses) > 0:
          html += '<DT>'+_('Uses')+':</DT><DD>' + HyperScan(listItemHtml(self.uses)) + '</DD>'
        if len(self.used) > 0:
          html += '<DT>'+_('Used')+':</DT><DD>' + HyperScan(listItemHtml(self.used)) + '</DD>'
        if 'throws' in JavaDocVars['otypes'][self.objectType]['otags'] and len(self.throws) > 0:
          html += '<DT>'+_('Throws Exception')+':</DT><DD>' + HyperScan(listItemHtml(self.throws)) + '</DD>'
        if len(self.bug) > 0:
          html += '<DT>'+_('BUG')+':</DT><DD>' + HyperScan(listItemHtml(self.bug)) + '</DD>'
        if len(self.deprecated) > 0:
          html += '<DT>'+_('DEPRECATED')+':</DT><DD>' + HyperScan(listItemHtml(self.deprecated)) + '</DD>'
        if len(self.version) > 0:
          html += '<DT>'+_('Version Info')+':</DT><DD>' + HyperScan(listItemHtml(self.version)) + '</DD>'
        if len(self.info) > 0:
          html += '<DT>'+_('Additional Info')+':</DT><DD>' + HyperScan(listItemHtml(self.info)) + '</DD>'
        if len(self.verbatim) > 0:
            html += '<DT>'+_('Verbatim')+':</DT>'
            for p in range(len(self.verbatim)):
                html += '<DD class="verbatim">' + self.verbatim[p] + '</DD>'
        if len(self.ticket) > 0:
          html += '<DT>'+_('Ticket')+':</DT>'
          for i in range(len(self.ticket)):
            html += '<DD>'
            if JavaDocVars['ticket_url'] != '':
              doc = self.ticket[i].split(' ');
              if doc[0].isdigit():
                html += '<A HREF="'+JavaDocVars['ticket_url'].replace('%{id}',doc[0])+'">#'+doc[0]+'</A>'
                html += self.ticket[i][len(doc[0]):]
              else:
                html += self.ticket[i]
            else:
              html += self.ticket[i]
            html += '</DD>'
        if len(self.wiki) > 0:
          html += '<DT>'+_('Wiki')+':</DT>'
          for i in range(len(self.wiki)):
            html += '<DD>'
            if JavaDocVars['wiki_url'] != '':
              doc = self.wiki[i].split(' ')
              html += '<A HREF="'+JavaDocVars['wiki_url'].replace('%{page}',doc[0])+'">'+doc[0]+'</A>'+self.wiki[i][len(doc[0]):]
            else:
              html += self.wiki[i]
            html += '</DD>'
        if len(self.see) > 0:
          html += '<DT>'+_('See also')+':</DT><DD>' + HyperScan(listItemHtml(self.see)) + '</DD>'
        if len(self.todo) > 0:
          html += '<DT>'+_('TODO')+':</DT><DD>' + HyperScan(listItemHtml(self.todo)) + '</DD>'
        html += '\n</DL>\n'
        if self.objectType not in JavaDocVars['supertypes']:
          html += '<DIV CLASS="toppagelink"><A HREF="#topOfPage">'+_('^ Top')+'</A></DIV>\n'
          html += '</TD></TR></TABLE>\n'
        return html
    def getShortDesc(self):
        """
        Generate a short desc from the given desc.
        Truncates after the first occurence of "?!.;\\n" - whichever from this
        characters comes first
        @param self
        @return string short_desc
        """
        if len(self.desc) < 1:
          return ''
        if JavaDocVars['javadoc_shortdesc_mode'] == 'line':
          shorty = re.match(r"""(.+?(\n)|.+)""",self.desc[0])
        else:
          shorty = re.match(r"""(.+?([\.\!\?;]\s|\n)|.+)""",self.desc[0])
        return shorty.group(1).strip() or self.desc[0]


class JavaDocParam:
    """ Parameters passed to a function/Procedure. Used by JavaDoc.params and JavaDoc.retVals """
    def __init__(self):
        """
        Initializes properties with useful defaults.
        @param self
        """
        self.inout = 'in' # 'in', 'out', or 'inout'. Ignored for retVals
        self.sqltype = 'VARCHAR2'
        self.default = ''
        self.desc = ''
        self.name = ''


class TaskItem:
    """ Task for Todo / Bug lists """
    def __init__(self,name='',line='',author='',uid=0):
        """
        Initializes properties with useful defaults.
        @param self
        @param optional name default ''
        @param optional desc default ''
        @param optional string author default ''
        @param optional int uid default 0
        """
        self.name = name
        self.desc = line
        self.author = author
        self.uid = uid

class TaskList:
    """
    List of TaskItems for Bugs / Todos
    Has a name and maintains a list of items
    Properties: String name, List items (list of TaskItem)
    """
    def __init__(self,name=''):
        """
        Initialize properties with useful defaults
        @param self
        @param optional string name
        """
        self.name  = name
        self.items = []
    def __repr__(self):
        """
        Debug helper
        """
        desc = '<hypercore.javadoc.TaskList>:\n' \
             + '* name:  '+self.name+'\n' \
             + '* items: '+str(len(self.items))
        return desc
    def addItem(self,name,desc,author='',uid=0):
        """
        Add an item to the tasklist.
        @param self
        @param string name
        @param string desc
        @param optional string author default ''
        @param optional int uid default 0
        """
        self.items.append(TaskItem(name,desc,author,uid))
    def taskCount(self):
        """
        Give the number of tasks in this list
        @param self
        @return int
        """
        return len(self.items)
    def itemSort(self,orderBy='name'):
        """
        Sort the tasks
        @param self
        @param optional string orderBy 'name' (default) or 'desc'
        """
        if orderBy=='desc':
            self.items.sort(key=lambda x: (x.desc,x.name,x.uid))
        else:
            self.items.sort(key=lambda x: (x.name,x.uid,x.desc))
    def getHtml(self):
        """
        Return collected tasks as unordered HTML list
        @param self
        @return string html
        """
        if self.taskCount() < 1: return ''
        html = '<UL>\n'
        for item in self.items: html += '  <LI>'+item.desc+'</LI>\n'
        html += '</UL>\n'
        return html

class PackageTaskList(TaskList):
    """
    TaskList for packages
    This is an extension to the TaskList class, considering the speciality a
    package holds multiple other objects.
    As its parent, it has a name and maintains a list of items (package-specific
    tasks). Additionally, it maintains similar lists for function- and procedure-
    specific tasks.
    """
    def __init__(self,name=''):
        """
        Initialize properties with useful defaults
        @param self
        @param optional string name (default: '')
        """
        TaskList.__init__(self,name)
        self.funcs = []
        self.procs = []
        self.pkgs  = [] # for form pkgs
        self.parent = None
    def __repr__(self):
        """
        Debug helper
        """
        desc = '<hypercore.javadoc.PackageTaskList>:\n' \
             + '* name  : '+self.name+'\n' \
             + '* items : '+str(len(self.items))+'\n' \
             + '* funcs : '+str(len(self.funcs))+'\n' \
             + '* procs : '+str(len(self.procs))+'\n' \
             + '* pkgs  : '+str(len(self.pkgs))
        #if self.parent: desc += '* parent: '+self.parent+'\n'
        #else: desc += '* parent: None'
        return desc
    def addFunc(self,name,desc,author='',uid=0):
        """
        Add an item to this packages function task list
        @param self
        @param string name
        @param string desc
        @param optional string author default ''
        @param optional int uid default 0
        """
        item = TaskItem(name,desc,author,uid);
        item.parent = self
        self.funcs.append(item)
    def addProc(self,name,desc,author='',uid=0):
        """
        Add an item to this packages procedure task list
        @param self
        @param string name
        @param string desc
        @param optional string author default ''
        """
        item = TaskItem(name,desc,author,uid);
        item.parent = self
        self.procs.append(item)
    def funcCount(self):
        """
        How many function tasks we have for this package?
        @param self
        @return number tasks
        """
        return len(self.funcs)
    def procCount(self):
        """
        How many procedure tasks we have for this package?
        @param self
        @return number tasks
        """
        return len(self.procs)
    def allItemCount(self):
        """
        How many tasks we have for this package altogether?
        @param self
        @return number tasks
        """
        allcount = 0
        for tlist in self.pkgs:
            allcount += ( tlist.allItemCount() )
        return allcount + self.taskCount() + self.funcCount() + self.procCount()
    def sortAll(self,orderBy='name'):
        """
        Sort all task lists of this package
        @param self
        @param optional string orderBy 'name' (default) or 'desc'
        """
        self.itemSort(orderBy)
        self.sortFuncs(orderBy)
        self.sortProcs(orderBy)
    def sortFuncs(self,orderBy='name'):
        """
        Sort this packages function task list
        @param self
        @param optional string orderBy 'name' (default) or 'desc'
        """
        if orderBy == 'desc':
            self.funcs.sort(key=lambda x: (x.desc,x.name,x.uid))
        else:
            self.funcs.sort(key=lambda x: (x.name,x.uid,x.desc))
    def sortProcs(self,orderBy='name'):
        """
        Sort this packages procedure task list
        @param self
        @param optional string orderBy 'name' (default) or 'desc'
        """
        if orderBy == 'desc':
            self.procs.sort(key=lambda x: (x.desc,x.name,x.uid))
        else:
            self.procs.sort(key=lambda x: (x.name,x.uid,x.desc))
    def getSubHtml(self,objectType):
        """
        Generate the Table BODY for tasks of the specified objectType
        This does not include the table opening and closing tags, but includes
        the special TH line. Table has 2 columns.
        @param self
        @param string objectType 'funcs' or 'procs'
        @return string html
        """
        if objectType == 'funcs':
            if len(self.funcs) < 1: return ''
            self.sortFuncs('name')
            items = self.funcs
            html = '  <TR><TH CLASS="sub">'+_('Function')+'</TH><TH CLASS="sub">'+_('Task')+'</TH>\n'
        else:
            if len(self.procs) < 1: return ''
            self.sortProcs('name')
            items = self.procs
            html = '  <TR><TH CLASS="sub">'+_('Procedure')+'</TH><TH CLASS="sub">'+_('Task')+'</TH>\n'
        name = ''
        uid = -1
        inner = ''
        author = ''
        for item in items:
            if item.name == name and item.uid == uid:
                inner += '<LI>'+item.desc+'</LI>'
            elif inner != '':
                if JavaDocVars['author_in_report']:
                    if author!='':
                        html += '  <TR><TD VALIGN="top"><B>'+name+'</B><BR>'+author+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
                    else:
                        html += '  <TR><TD VALIGN="top"><B>'+name+'</B></TD><TD><UL>'+inner+'</UL></TD></TR>\n'
                else:
                    html += '  <TR><TD VALIGN="top">'+name+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
                inner  = '<LI>'+item.desc+'</LI>'
                name   = item.name
                uid    = item.uid
                if len(item.author)>0: author = '('+_('Author')+': '+', '.join(item.author)+')'
                else: author = ''
            else:
                inner += '<LI>'+item.desc+'</LI>'
                name   = item.name
                uid    = item.uid
                if len(item.author)>0: author = '('+_('Author')+': '+', '.join(item.author)+')'
                else: author = ''
        if inner !='':
            if JavaDocVars['author_in_report']:
                if author!='':
                    html += '  <TR><TD VALIGN="top"><B>'+name+'</B><BR>'+author+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
                else:
                    html += '  <TR><TD VALIGN="top"><B>'+name+'</B></TD><TD><UL>'+inner+'</UL></TD></TR>\n'
            else:
                html += '  <TR><TD VALIGN="top">'+name+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
        return html
    def getFuncHtml(self):
        """
        Generate HTML for function task list (wrapper to getSubHtml)
        @param self
        @return string html
        """
        return self.getSubHtml('funcs')
    def getProcHtml(self):
        """
        Generate HTML for procedure task list (wrapper to getSubHtml)
        @param self
        @return string html
        """
        return self.getSubHtml('procs')
    def getSubPkgHtml(self):
        """
        Generate HTML for sub-packages (e.g. Oracle Forms packages)
        @param self
        @return string html
        """
        if len(self.pkgs)==0: return ''
        html = ''
        for pkg in self.pkgs:
          if pkg.allItemCount()<1: continue
          html += '  <TR><TD CLASS="sub" COLSPAN="2"><B><I>'+_('Package')+' '+pkg.name.lower()+'</I></B></TD></TR>\n'
          if pkg.taskCount()>0:
            html += '  <TR><TD COLSPAN="2"><UL>'
            for item in pkg.items: html += '<LI>'+item.desc+'</LI>'
            html += '</UL></TD></TR>\n'
          html += pkg.getFuncHtml()
          html += pkg.getProcHtml()
        return html


def ScanJavaDoc(text,fileName,lineNo=0):
    """
    Scans the text array (param 1) for the javadoc style comments starting at
    line lineNo (param 3) if defined - otherwise at line 0. Called from
    ScanFilesForViewsAndPackages.
    Returns a list of instances of the JavaDoc class - one instance per javadoc
    comment block.
    @param string text to parse
    @param string fileName name of the file this text is from (for eventual error messages)
    @param optional number lineNo which line to start with (Default: 0, the very beginning)
    @return list of JavaDoc instances
    """
    if is_list(text): text = ''.join(text)
    reTagEnd    = r'(\n\s*\**\s*@|\*\/)' # end of tag/desc definition
    reLineStart = r'(\n\s*\**\s*)'       # start of a line, incl. optional '*'
    pattLeading = re.compile(r'^\s*\**\s*')
    pattTag     = re.compile(reLineStart+r'(@\w+)([ \t\f\v]*)([^\n]*.*?)\s*'+reTagEnd, re.M|re.S|re.I)
    pattBreak   = re.compile(reLineStart) # line break inside a tag desc

    blocks = []
    items  = []
    for m in re.finditer(r'/\*\*(.*?)\*/', text, re.M|re.S): # Collect JavaDoc blocks w/ their position
        start = m.start()
        lineno = text.count('\n', 0, start) +1 # starts at line 0
        offset = start - text.rfind('\n', 0, start)
        block = m.group(0)
        blocks.append((lineno, offset, block))

    for tblock in blocks:                                    # Parse JavaDoc blocks
        if tblock[0]+1<lineNo: continue
        lineNumber = tblock[0]+1
        block = tblock[2].strip()
        item = JavaDoc()
        item.file = fileName
        item.lineNumber = lineNumber
        item.file = fileName
        tdesc = re.search(r'\*\*\s*(.*?)\s*'+reTagEnd,block,re.M|re.S).group(1).strip()
        if tdesc != '':
            desc = tdesc.split('\n')
            for i in range(len(desc)): desc[i] = pattLeading.sub('',desc[i]).strip()
            if desc[0][0]!='@': item.desc = desc
        tags = pattTag.search(block)
        lineNumber = tblock[0]+tdesc.count('\n')+1 # the line following the desc
        taglines = 0
        while tags != None:
            tag  = tags.group(2)[1:].lower().strip()
            cont = pattBreak.sub(' ',tags.group(4))
            if tag!='verbatim':
                cont = cont.strip()
            taglines = tags.group(0).strip().count('\n')
            end = tags.start()+len(tags.group(1)+tags.group(2)+tags.group(3)+tags.group(4))
            tags = pattTag.search(block,end)
            if tag in JavaDocVars['otypes']:
                if cont=='':
                    logger.info(_('object type %(otype)s must have an object name specified, none was given in %(file)s line %(line)s'), {'otype':item.objectType, 'file':fileName, 'line':lineNumber})
                else:
                    item.objectType = tag
                    item.name = cont
            elif tag in JavaDocVars['tags']:
                if tag == 'param':    # @param inout type [name [desc]]
                    if cont=='':
                      logger.info(_('@param requires at least one parameter, none given in %(file)s line %(line)s'), {'file':fileName, 'line':lineNumber})
                    else:
                      p = JavaDocParam()
                      doc = cont.split()
                      if doc[0].lower() in ['in','out','inout']:
                        p.inout   = doc[0].upper()
                        p.sqltype = doc[1].upper()
                        if len(doc) > 2:
                          p.name = doc[2]
                          for w in range(3,len(doc)):
                            p.desc += doc[w] + ' '
                          p.desc = p.desc.strip()
                      else:
                          p.sqltype = doc[0]
                          if len(doc) > 1:
                              p.name = doc[1]
                              for w in range(2,len(doc)):
                                p.desc += doc[w] + ' '
                              p.desc = p.desc.strip()
                      item.params.append(p)
                elif tag in JavaDocVars['txttags']:
                    if cont=='':
                      logger.info(_('@%(tag)s requires <text> parameter, none given in %(file)s line %(line)s'), {'tag':tag, 'file':fileName, 'line':lineNumber})
                    else:
                      item.__getattribute__(tag).append(cont)
                elif tag in ['return','col']: # @(return|col) type [name [desc]]
                  if cont=='':
                    logger.info(_('@%(tag)s requires at least one parameter, none given in %(file)s line %(line)s'), {'tag':tag,'file':fileName, 'line':lineNumber})
                  else:
                    p = JavaDocParam()
                    doc = cont.split()
                    p.sqltype = doc[0].upper()
                    if len(doc)>1:
                      p.name = doc[1]
                      for w in range(2,len(doc)):
                        p.desc += doc[w] + ' '
                    if (tag=='return'): item.retVals.append(p)
                    else: item.cols.append(p)
                elif tag == 'private': item.private = True
                elif tag == 'ignore' : item.ignore  = True
                elif tag == 'ignorevalidation' : item.ignorevalidation = True
                else: # kick the developers brain - one never should get here!
                    logger.warn(_('JavaDoc tag "%s" failed - kick the developers brain!'), tag)
            else:             # unsupported tag, ignore
                logger.info(_('unsupported JavaDoc tag "%(tag)s" in %(file)s line %(line)s'), {'tag':tag, 'file':fileName, 'line':lineNumber})
                lineNumber += taglines
                continue
            lineNumber += taglines
        items.append(item)
    return items
