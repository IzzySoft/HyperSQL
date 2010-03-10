"""
$Id$
HyperSQL Javadoc support
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from sys import maxint
import logging, re
logger = logging.getLogger('main.jdoc')

JavaDocVars = dict(
    wiki_url     = '',
    ticket_url = '',
    top_level_dir_len = 0,
    verification = False,
    mandatory_tags = [],
    otypes = ['function', 'procedure', 'view', 'pkg'], # supported object types
    tags   = ['param', 'return', 'version', 'author', 'info', 'example',
              'todo', 'bug', 'copyright', 'deprecated', 'private',
              'see', 'webpage', 'license', 'ticket', 'wiki'], # other supported tags
    txttags = ['version', 'author', 'info', 'example', 'todo', 'bug',
               'copyright', 'deprecated', 'see', 'webpage', 'license',
               'ticket', 'wiki', 'desc'] # values of these tags are plain text
)

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

class JavaDoc:
    """
    Object to hold details from javadoc style comments
    """
    def __init__(self):
        """
        Initializes all properties with useful defaults.
        """
        self.file = ''
        self.lineNumber = -1
        self.lines = 0
        self.name = ''
        self.objectType = ''
        self.params = []
        self.retVals = []
        self.desc = ''
        self.version = ''
        self.author = ''
        self.info = ''
        self.example = ''
        self.todo = ''
        self.bug = ''
        self.copyright = ''
        self.deprecated = ''
        self.private = False
        self.see = ''
        self.webpage = ''
        self.license = ''
        self.file = ''
        self.ticket = ''
        self.wiki = ''
        self.lndiff = maxint # needed for function/procedure overloading
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
        if self.isDefault() or not JavaDocVars['verification']:
            return faillist
        for tag in JavaDocVars['mandatory_tags']:
            if tag in JavaDocVars['txttags'] and eval("self." + tag) == '':
                if tag == 'desc':
                    faillist.append('Missing description')
                else:
                    faillist.append('Missing mandatory tag: @'+tag)
                logger.warn('Missing mandatory tag "%s" for %s %s in %s line %s', tag, self.objectType, self.name, self.file[JavaDocVars['top_level_dir_len']+1:], self.lineNumber)
        for param in self.params:
            if param.name == '':
                faillist.append('Missing name for '+param.sqltype+' parameter (#'+`self.params.index(param)`+')')
                logger.warn('Missing name for parameter of type "%s" for %s %s in %s line %s', param.sqltype, self.objectType, self.name, self.file[JavaDocVars['top_level_dir_len']+1:], self.lineNumber)
            if param.desc == '':
                if param.name == '':
                    faillist.append('Missing description for '+param.sqltype+' parameter (#'+`self.params.index(param)`+')')
                    logger.warn('Missing description for parameter of type "%s" for %s %s in %s line %s', param.sqltype, self.objectType, self.name, self.file[JavaDocVars['top_level_dir_len']+1:], self.lineNumber)
                else:
                    faillist.append('Missing description for parameter '+param.name)
                    logger.warn('Missing description for parameter "%s" for %s %s in %s line %s', param.name, self.objectType, self.name, self.file[JavaDocVars['top_level_dir_len']+1:], self.lineNumber)
        if self.objectType == 'function' and len(self.retVals)<1:
            faillist.append('Missing return value')
            logger.warn('Missing return value for function %s in %s line %s', self.name, self.file[JavaDocVars['top_level_dir_len']+1:], self.lineNumber)
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
        if self.isDefault():
            return ''
        if self.objectType not in JavaDocVars['otypes']:
            if self.name == '':
                logger.warn('Unnamed object with ID %s (%s line %s has no object type set!', unum, self.file, self.lineNumber)
            else:
                logger.warn('No object type specified for object id %s, ID %s in %s line %s', self.name, unum, self.file, self.lineNumber)
            return ''
        html = ''
        if self.objectType != 'pkg':
          html = '<A NAME="'+self.name+'_'+str(unum)+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom:10px" WIDTH="95%"><TR><TH>' + self.name + '</TH>\n'
          html += '<TR><TD>\n';
        if self.desc != '':
          html += '  <DIV CLASS="jd_desc">' + HyperScan(self.desc) + '</DIV>\n'
        html += '  <DL>'
        if self.objectType in ['function', 'procedure']:
          if self.private:
            html += ' <DT>Private</DT><DD>Just used internally.</DD>'
          html += '  <DT>Syntax:</DT><DD><DIV STYLE="margin-left:15px;text-indent:-15px;">' + self.name + ' ('
          for p in range(len(self.params)):
            html += self.params[p].name
            if p<len(self.params)-1:
              html += ', '
          html += ')</DIV></DD>\n'
          if len(self.params) > 0 and self.objectType != 'pkg':
            html += ' <DT>Parameters:</DT><DD>'
            for p in range(len(self.params)):
              html += '<DIV STYLE="margin-left:15px;text-indent:-15px;">' + self.params[p].inout + ' ' + self.params[p].sqltype + ' <B>' + self.params[p].name + '</B>'
              if self.params[p].desc != '':
                html += ': ' + self.params[p].desc
              html += '</DIV>'
            html += '</DD>\n'
          if self.objectType == 'function':
            html += ' <DT>Return values:</DT><DD><UL STYLE="list-style-type:none;margin-left:-40px;">'
            for p in range(len(self.retVals)):
              html += '<LI>' + self.retVals[p].sqltype + ' <B>' + self.retVals[p].name + '</B>'
              if self.retVals[p].desc != '':
                html += ': ' + self.retVals[p].desc
              html += '</LI>'
            html += '</UL></DD>\n'
          if self.example != '':
            html += '<DT>Example Usage:</DT><DD>' + self.example + '</DD>'
        if self.author != '':
          html += '<DT>Author:</DT><DD>' + self.author + '</DD>'
        if self.copyright != '':
          html += '<DT>Copyright:</DT><DD>' + self.copyright + '</DD>'
        if self.license != '':
          html += '<DT>License:</DT><DD>' + self.license + '</DD>'
        if self.webpage != '':
          html += '<DT>Webpage:</DT><DD><A HREF="' + self.webpage + '">' + self.webpage + '</A></DD>'
        if self.bug != '':
          html += '<DT>BUG:</DT><DD>' + HyperScan(self.bug) + '</DD>'
        if self.deprecated != '':
          html += '<DT>DEPRECATED:</DT><DD>' + HyperScan(self.deprecated) + '</DD>'
        if self.version != '':
          html += '<DT>Version Info:</DT><DD>' + HyperScan(self.version) + '</DD>'
        if self.info != '':
          html += '<DT>Additional Info:</DT><DD>' + HyperScan(self.info) + '</DD>'
        if self.ticket != '':
          html += '<DT>Ticket:</DT><DD>'
          if JavaDocVars['ticket_url'] != '':
            doc = self.ticket.split(' ');
            if doc[0].isdigit():
              html += '<A HREF="'+JavaDocVars['ticket_url'].replace('%{id}',doc[0])+'">#'+doc[0]+'</A>'
              html += self.ticket[len(doc[0]):]
            else:
              html += self.ticket
          else:
            html += self.ticket
          html += '</DD>'
        if self.wiki != '':
          html += '<DT>Wiki:</DT><DD>'
          if JavaDocVars['wiki_url'] != '':
            doc = self.wiki.split(' ')
            html += '<A HREF="'+JavaDocVars['wiki_url'].replace('%{page}',doc[0])+'">'+doc[0]+'</A>'+self.wiki[len(doc[0]):]
          else:
            html += self.wiki
          html += '</DD>'
        if self.see != '':
          html += '<DT>See also:</DT><DD>' + HyperScan(self.see) + '</DD>'
        if self.todo != '':
          html += '<DT>TODO:</DT><DD>' + HyperScan(self.todo) + '</DD>'
        html += '\n</DL>\n'
        if self.objectType != 'pkg':
          html += '<DIV CLASS="toppagelink"><A HREF="#topOfPage">^ Top</A></DIV>\n'
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
        dot = []
        if self.desc.find('?')>0:
          dot.append( self.desc.find('?') )
        if self.desc.find('!')>0:
          dot.append( self.desc.find('!') )
        if self.desc.find('.')>0:
          dot.append( self.desc.find('.') )
        if self.desc.find(';')>0:
          dot.append( self.desc.find(';') )
        if self.desc.find('\n')>0:
          dot.append( self.desc.find('\n') )
        if len(dot)>0:
          cut = min(dot)
          return self.desc[0:cut]
        else:
          return self.desc


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
    def __init__(self,name='',line=''):
        """
        Initializes properties with useful defaults.
        @param self
        @param optional name default ''
        @param optional desc default ''
        """
        self.name = name
        self.desc = line

def taskSortDesc(a,b):
    """
    Helper for sorting a TaskList by descriptions
    @param TaskItem a
    @param TaskItem b
    """
    if a.desc < b.desc:
        return -1
    elif a.desc > b.desc:
        return 1
    else:
        if a.name < b.name:
            return -1
        if a.name > b.name:
            return 1
        else:
            return 0

def taskSortName(a,b):
    """
    Helper for sorting a TaskList by names
    @param TaskItem a
    @param TaskItem b
    """
    if a.name < b.name:
        return -1
    elif a.name > b.name:
        return 1
    else:
        if a.desc < b.desc:
            return -1
        if a.desc > b.desc:
            return 1
        else:
            return 0

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
    def addItem(self,name,desc):
        """
        Add an item to the tasklist.
        @param self
        @param string name
        @param string desc
        """
        self.items.append(TaskItem(name,desc))
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
        if self.taskCount < 1:
            return ''
        html = '<UL>\n'
        for item in self.items:
            html += '  <LI>'+item.desc+'</LI>\n'
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
    def addFunc(self,name,desc):
        """
        Add an item to this packages function task list
        @param self
        @param string name
        @param string desc
        """
        item = TaskItem(name,desc);
        item.parent = self
        self.funcs.append(item)
    def addProc(self,name,desc):
        """
        Add an item to this packages procedure task list
        @param self
        @param string name
        @param string desc
        """
        item = TaskItem(name,desc);
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
            if len(self.funcs) < 1:
                return ''
            self.sortFuncs('name')
            items = self.funcs
            html = '  <TR><TH CLASS="sub">Function</TH><TH CLASS="sub">Task</TH>\n'
        else:
            if len(self.procs) < 1:
                return ''
            self.sortProcs('name')
            items = self.procs
            html = '  <TR><TH CLASS="sub">Procedure</TH><TH CLASS="sub">Task</TH>\n'
        name = ''
        inner = ''
        for item in items:
            if item.name == name:
                inner += '<LI>'+item.desc+'</LI>'
            elif inner != '':
                html += '  <TR><TD VALIGN="top">'+name+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
                inner = '<LI>'+item.desc+'</LI>'
                name  = item.name
            else:
                inner += '<LI>'+item.desc+'</LI>'
                name = item.name
        if inner !='':
            html += '  <TR><TD>'+name+'</TD><TD><UL>'+inner+'</UL></TD></TR>\n'
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
    res  = []
    opened = False
    otypes = JavaDocVars['otypes'] # supported object types
    tags   = JavaDocVars['tags']   # other supported tags
    for lineNumber in range(lineNo,len(text)):
      line = text[lineNumber].strip()
      if not opened and line[0:3] != '/**':
        continue
      if line[0:1] == '*' and line[0:2] != '*/':
        line = line[1:].strip()
      if line == '*/':
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
          item.desc += line[3:].strip()
          continue
        if line[0:1] != '@':
          if line[len(line)-2:] == '*/':
            item.desc += line[0:len(line)-2]
            res.append(item)
            opened = False
            elem = 'desc'
            continue
          else:
            if item.desc == '':
              item.desc = line
            else:
              item.desc += '\n' + line
            continue
        else:
          elem = ''
      if elem != 'desc':
        if line[0:1] != '@': # 2nd+ line of a tag
          if elem in tags and elem not in ['param','return','private']: # maybe...
            exec('item.'+elem+' += " '+line.replace('"','&quot;')+'"')
          continue
        doc = line.split()
        tag = doc[0][1:]
        elem = tag
        if tag in otypes: # line describes supported object type + name
          item.objectType = doc[0][1:]
          item.name = doc[1]
        elif tag in tags: # other supported tag
          if tag == 'param':    # @param inout type [name [desc]]
            if len(doc) < 2:
              logger.warn('@param requires at least one parameter, none given in %s line %s', fileName, lineNumber)
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
          elif tag == 'return': # @return type [name [desc]
            if len(doc) < 2:
              logger.warn('@return requires at least one parameter, none given in %s line %s', fileName, lineNumber)
            else:
              p = JavaDocParam()
              p.sqltype = doc[1].upper()
              if len(doc)>2:
                p.name = doc[2]
                for w in range(3,len(doc)):
                  p.desc += doc[w] + ' '
              item.retVals.append(p)
          elif tag == 'private':
            item.private = True
          else: # tags with only one <text> parameter
            if len(doc) < 2:
              logger.warn('@%s requires <text> parameter, none given in %s line %s', tag, fileName, lineNumber)
            elif tag == 'version':
              item.version = line[len(tag)+1:].strip()
            elif tag == 'author':
              item.author = line[len(tag)+1:].strip()
            elif tag == 'info':
              item.info = line[len(tag)+1:].strip()
            elif tag == 'example':
              item.example = line[len(tag)+1:].strip()
            elif tag == 'todo':
              item.todo = line[len(tag)+1:].strip()
            elif tag == 'bug':
              item.bug = line[len(tag)+1:].strip()
            elif tag == 'copyright':
              item.copyright = line[len(tag)+1:].strip()
            elif tag == 'deprecated':
              item.deprecated = line[len(tag)+1:].strip()
            elif tag == 'see':
              item.see = line[len(tag)+1:].strip()
            elif tag == 'webpage':
              item.webpage = line[len(tag)+1:].strip()
            elif tag == 'license':
              item.license = line[len(tag)+1:].strip()
            elif tag == 'ticket':
              item.ticket = line[len(tag)+1:].strip()
            elif tag == 'wiki':
              item.wiki = line[len(tag)+1:].strip()
            else:
              logger.debug('Ooops - tag %s not handled?', tag)
        else:             # unsupported tag, ignore
          logger.warn('unsupported JavaDoc tag "%s" in %s line %s', tag, fileName, lineNumber)
          continue
        
    return res

