"""
$Id$
HyperSQL Javadoc support
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from .gettext_init import langpath, langs
from sys import maxint, argv as pargs
import logging, re, gettext, locale, os
logger = logging.getLogger('main.jdoc')

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
    javadoc_mandatory = False,
    verification = False,
    verification_log = False,
    author_in_report = False,
    mandatory_tags = [],
    otypes = {}, # supported object types
    supertypes = [], # object types with subobjects
    tags   = ['param', 'return', 'version', 'author', 'info', 'example',
              'todo', 'bug', 'copyright', 'deprecated', 'private',
              'see', 'webpage', 'license', 'ticket', 'wiki', 'since',
              'uses', 'ignore', 'throws', 'col', 'used'], # other supported tags
    txttags = ['version', 'author', 'info', 'example', 'todo', 'bug',
               'copyright', 'deprecated', 'see', 'webpage', 'license',
               'ticket', 'wiki', 'desc', 'since', 'uses', 'throws',
               'used'] # values of these tags are plain text
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
        self.see = []
        self.webpage = []
        self.license = []
        self.ticket = []
        self.wiki = []
        self.since = []
        self.uses = []
        self.used = []
        self.throws = []

    def __repr__(self):
        """ Basic information for simple debug """
        if self.isDefault(): return 'empty JavaDoc object'
        if self.objectType: ret = self.objectType
        else: ret = 'unknown object'
        if self.name: ret += ' ' + self.name
        if self.file:
            ret += ' from ' + self.file
            if self.lineNumber!=-1: ret += ' at line ' + `self.lineNumber`
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
        if self.isDefault() or self.ignore or not JavaDocVars['verification']:
            return faillist
        for tag in JavaDocVars['mandatory_tags']:
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
                faillist.append(_('Missing name for %(type)s parameter (#%(index)s)') % {'type': param.sqltype, 'index': `self.params.index(param)`})
                self.log(_('Missing name for parameter of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':param.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
            if param.desc == '' and 'desc' in JavaDocVars['mandatory_tags']:
                if param.name == '':
                    faillist.append(_('Missing description for %(type)s parameter (#%(index)s)') % {'type':param.sqltype, 'index':`self.params.index(param)`})
                    self.log(_('Missing description for parameter of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':param.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
                else:
                    faillist.append(_('Missing description for parameter %s') % param.name)
                    self.log(_('Missing description for parameter "%(pname)s" for %(otype)s %(oname)s in %(file)s line %(line)s') % {'pname':param.name, 'otype':self.objectType, 'oname':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        for col in self.cols:
            if col.name == '':
                faillist.append(_('Missing name for %(type)s column (#%(index)s)') % {'type': col.sqltype, 'index': `self.cols.index(col)`})
                self.log(_('Missing name for column of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':col.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
            if col.desc == '' and 'desc' in JavaDocVars['mandatory_tags']:
                if col.name == '':
                    faillist.append(_('Missing description for %(type)s column (#%(index)s)') % {'type':col.sqltype, 'index':`self.cols.index(col)`})
                    self.log(_('Missing description for column of type "%(type)s" for %(otype)s %(name)s in %(file)s line %(line)s') % {'type':col.sqltype, 'otype':self.objectType, 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
                else:
                    faillist.append(_('Missing description for column %s') % col.name)
                    self.log(_('Missing description for column "%(pname)s" for %(otype)s %(oname)s in %(file)s line %(line)s') % {'pname':col.name, 'otype':self.objectType, 'oname':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
        if 'return' in JavaDocVars['otypes'][self.objectType]['otags'] and len(self.retVals)<1:
            faillist.append(_('Missing return value'))
            self.log(_('Missing return value for %(otype)s %(name)s in %(file)s line %(line)s') % {'otype':JavaDocVars[self.objectType]['name'], 'name':self.name, 'file':self.file[JavaDocVars['top_level_dir_len']+1:], 'line':self.lineNumber})
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
            faillist.append(_('Parameter count mismatch: Code has %(cparms)s parameters, Javadoc %(jparms)s') % { 'cparms':`len(cparms)`, 'jparms':`len(self.params)`})
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
    def getHtml(self,unum):
        """
        Generates HTML block from JavaDoc Api Info for the element passed - or
        an empty string if it is still the default empty element.
        @param self
        @param int unique number
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
                self.log(_('Unnamed object with ID %(id)s (%(file)s line %(line)s has no object type set!') % {'id':unum, 'file':self.file, 'line':self.lineNumber})
            else:
                self.log(_('No object type specified for object id %(name)s, ID %(id)s in %(file)s line %(line)s') % {'name':self.name, 'id':unum, 'file':self.file, 'line':self.lineNumber})
            return ''
        html = ''
        if self.objectType not in JavaDocVars['supertypes']:
          html = '<A NAME="'+self.name+'_'+str(unum)+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom:10px" WIDTH="95%"><TR><TH>' + self.name + '</TH>\n'
          html += '<TR><TD>\n';
        if len(self.desc) > 0:
          html += '  <DIV CLASS="jd_desc">'
          for i in range(len(self.desc)):
            html += HyperScan(self.desc[i]) 
          html += '</DIV>\n'
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
              html += '<TR CLASS="tr'+`i`+'"><TD>' + self.params[p].name + '</TD>'
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
            html += '<TR CLASS="tr'+`i`+'"><TD>' + self.cols[p].name + '</TD>'
            html += '<TD>' + self.cols[p].sqltype + '</TD>'
            if self.cols[p].desc != '': html += '<TD>' + self.cols[p].desc + '</TD></TR>'
            else: html += '<TD>&nbsp;</TD></TR>'
            i = (i+1) % 2
          html += '</TABLE></DD>\n'

        if len(self.example) > 0:
          html += '<DT>'+_('Example Usage')+':</DT>'
          for i in range(len(self.example)):
            html += '<DD>' + self.example[i] + '</DD>'
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
        dot = []
        if self.desc[0].find('?')>0:
          dot.append( self.desc[0].find('?') )
        if self.desc[0].find('!')>0:
          dot.append( self.desc[0].find('!') )
        if self.desc[0].find('.')>0:
          dot.append( self.desc[0].find('.') )
        if self.desc[0].find(';')>0:
          dot.append( self.desc[0].find(';') )
        if self.desc[0].find('\n')>0:
          dot.append( self.desc[0].find('\n') )
        if len(dot)>0:
          cut = min(dot)
          return self.desc[0][0:cut]
        else:
          return self.desc[0]


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

def taskSortDesc(a,b):
    """
    Helper for sorting a TaskList by descriptions
    @param TaskItem a
    @param TaskItem b
    """
    if a.desc < b.desc:   return -1
    elif a.desc > b.desc: return 1
    else:
        if a.name < b.name:   return -1
        elif a.name > b.name: return 1
        else:
            if a.uid < b.uid:   return -1
            elif a.uid > b.uid: return 1
            else: return 0

def taskSortName(a,b):
    """
    Helper for sorting a TaskList by names
    @param TaskItem a
    @param TaskItem b
    """
    if a.name < b.name:   return -1
    elif a.name > b.name: return 1
    else:
        if a.uid < b.uid:   return -1
        elif a.uid > b.uid: return 1
        else:
            if a.desc < b.desc: return -1
            elif a.desc > b.desc: return 1
            else:               return 0

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
            self.items.sort(taskSortDesc)
        else:
            self.items.sort(taskSortName)
    def getHtml(self):
        """
        Return collected tasks as unordered HTML list
        @param self
        @return string html
        """
        if self.taskCount < 1: return ''
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
        return self.taskCount() + self.funcCount() + self.procCount()
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
            self.funcs.sort(taskSortDesc)
        else:
            self.funcs.sort(taskSortName)
    def sortProcs(self,orderBy='name'):
        """
        Sort this packages procedure task list
        @param self
        @param optional string orderBy 'name' (default) or 'desc'
        """
        if orderBy == 'desc':
            self.procs.sort(taskSortDesc)
        else:
            self.procs.sort(taskSortName)
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
            html = '  <TR><TH CLASS="sub">Function</TH><TH CLASS="sub">Task</TH>\n'
        else:
            if len(self.procs) < 1: return ''
            self.sortProcs('name')
            items = self.procs
            html = '  <TR><TH CLASS="sub">Procedure</TH><TH CLASS="sub">Task</TH>\n'
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
    elem = 'desc'
    content = ''
    res  = []
    opened = False
    otypes = JavaDocVars['otypes'] # supported object types
    tags   = JavaDocVars['tags']   # other supported tags
    txttags= JavaDocVars['txttags']# tags with just one parameter, type text
    for lineNumber in range(lineNo,len(text)):
      line = text[lineNumber].strip()
      if not opened and line[0:3] != '/**':
        continue
      if line[0:1] == '*' and line[0:2] != '*/':
        line = line[1:].strip()
      if line == '*/': # end of JavaDoc block
        if elem in txttags:
            exec('item.'+elem+'.append(content)')
        content = ''
        res.append(item)
        elem = 'desc'
        opened = False
        continue
      if elem == 'desc':
        if line[0:3] == '/**':
          opened = True
          item = JavaDoc()
          item.lineNumber = lineNumber
          item.file = fileName
          content = line[3:].strip().replace('"','&quot;')
          continue
        if line[0:1] != '@':
          if line[len(line)-2:] == '*/': # end of JavaDoc block
            content += ' ' + line[0:len(line)-2].replace('"','&quot;')
            item.desc.append(content)
            content = ''
            res.append(item)
            opened = False
            elem = 'desc'
            continue
          else:
            if content == '':
              content = line.replace('"','&quot;')
            else:
              content += ' ' + line
            item.desc.append(content)
            content = ''
            continue
        else:
          item.desc.append(content)
          content = ''
          elem = ''
      if elem != 'desc':
        if line[0:1] != '@': # 2nd+ line of a tag
          if elem in tags and elem not in ['param','return','private']: # maybe...
            content += ' ' + line.replace('"','&quot;')
          continue
        # new tag starts here
        if elem != '' and content != '' and elem in txttags: # there is something in the buffer
            exec('item.'+elem+'.append(content)')
            content = ''
        doc = line.split()
        tag = doc[0][1:]
        elem = tag
        if tag in otypes: # line describes supported object type + name
          item.objectType = doc[0][1:]
          item.name = doc[1]
        elif tag in tags: # other supported tag
          if tag == 'param':    # @param inout type [name [desc]]
            if len(doc) < 2:
              logger.info(_('@param requires at least one parameter, none given in %(file)s line %(line)s'), {'file':fileName, 'line':lineNumber})
            else:
              p = JavaDocParam()
              if doc[1] in ['in','out','inout']:
                p.inout   = doc[1].upper()
                p.sqltype = doc[2].upper()
                if len(doc) > 3:
                  p.name = doc[3]
                  for w in range(4,len(doc)):
                    p.desc += doc[w] + ' '
                  p.desc = p.desc.strip()
              else:
                p.sqltype = doc[1]
                if len(doc) > 2:
                  p.name = doc[2]
                  for w in range(3,len(doc)):
                    p.desc += doc[w] + ' '
                  p.desc = p.desc.strip()
              item.params.append(p)
          elif tag in ['return','col']: # @(return|col) type [name [desc]]
            if len(doc) < 2:
              logger.info(_('@%(tag)s requires at least one parameter, none given in %(file)s line %(line)s'), {'tag':tag,'file':fileName, 'line':lineNumber})
            else:
              p = JavaDocParam()
              p.sqltype = doc[1].upper()
              if len(doc)>2:
                p.name = doc[2]
                for w in range(3,len(doc)):
                  p.desc += doc[w] + ' '
              if (tag=='return'): item.retVals.append(p)
              else: item.cols.append(p)
          elif tag == 'private':
            item.private = True
          elif tag == 'ignore':
            item.ignore = True
          else: # tags with only one <text> parameter
            if len(doc) < 2:
              logger.info(_('@%(tag)s requires <text> parameter, none given in %(file)s line %(line)s'), {'tag':tag, 'file':fileName, 'line':lineNumber})
            content = line[len(tag)+1:].strip()
        else:             # unsupported tag, ignore
          logger.info(_('unsupported JavaDoc tag "%(tag)s" in %(file)s line %(line)s'), {'tag':tag, 'file':fileName, 'line':lineNumber})
          continue

    return res
