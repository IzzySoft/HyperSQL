"""
$Id$
HyperSQL Javadoc support
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

class JavaDoc:
    """Object to hold details from javadoc style comments"""
    def __init__(self):
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
    def isDefault(self):
        """Check if this is just an empty dummy (True), or if any real data have been assigned (False)"""
        if self.lineNumber != -1: return False
        return True
    def getHtml(self,unum):
        """
        Generates HTML block from JavaDoc Api Info for the element passed - or
        an empty string if it is still the default empty element.
        Param: instance of JavaDoc class, int unique number
        """
        if self.isDefault():
            return ''
        html = ''
        if self.objectType != 'pkg':
          html = '<A NAME="'+self.name+'_'+str(unum)+'"></A><TABLE CLASS="apilist" STYLE="margin-bottom:10px" WIDTH="95%" ALIGN="center"><TR><TH>' + self.name + '</TH>\n'
          html += '<TR><TD>\n';
        if self.desc != '':
          html += '  <DIV CLASS="jd_desc">' + self.desc + '</DIV>\n'
        html += '  <DL>'
        if self.objectType in ['function', 'procedure']:
          if self.private:
            html += ' <DT>Private</DT><DD>Just used internally.</DD>'
          html += '  <DT>Syntax:</DT><DD><DIV STYLE="margin-left:15px;text-indent:-15px;">' + self.name + ' ('
          for p in range(len(self.params)):
            html += self.params[p].name + ' ' + self.params[p].inout + ' ' + self.params[p].sqltype
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
          html += '<DT>BUG:</DT><DD>' + self.bug + '</DD>'
        if self.deprecated != '':
          html += '<DT>DEPRECATED:</DT><DD>' + self.deprecated + '</DD>'
        if self.version != '':
          html += '<DT>Version Info:</DT><DD>' + self.version + '</DD>'
        if self.info != '':
          html += '<DT>Additional Info:</DT><DD>' + self.info + '</DD>'
        if self.see != '':
          html += '<DT>See also:</DT><DD>' + self.see + '</DD>'
        if self.todo != '':
          html += '<DT>TODO:</DT><DD>' + self.todo + '</DD>'
        html += '\n</DL>'
        if self.objectType != 'pkg':
          html += '</TD></TR></TABLE>\n'
        return html
    def getShortDesc(self):
        """
        Generate a short desc from the given desc
        Truncates after the first occurence of "?!.;\n" - whichever from this
        characters comes first
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
    """Parameters passed to a function/Procedure. Used by JavaDoc.params and JavaDoc.retVals"""
    def __init__(self):
        self.inout = 'in' # 'in', 'out', or 'inout'. Ignored for retVals
        self.sqltype = 'VARCHAR2'
        self.default = ''
        self.desc = ''
        self.name = ''

def ScanJavaDoc(text,lineno=0):
    """
    Scans the text array (param 1) for the javadoc style comments starting at
    line lineno (param 2). Called from ScanFilesForViewsAndPackages.
    Returns a list of instances of the JavaDoc class - one instance per javadoc
    comment block.
    """
    elem = 'desc'
    res  = []
    opened = False
    otypes = ['function', 'procedure', 'view', 'pkg'] # supported object types
    tags   = ['param', 'return', 'version', 'author', 'info', 'example',
              'todo', 'bug', 'copyright', 'deprecated', 'private',
              'see', 'webpage', 'license'] # other supported tags
    for lineNumber in range(lineno,len(text)):
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
            exec('item.'+elem+' += " '+line+'"')
          continue
        doc = line.split()
        tag = doc[0][1:]
        elem = tag
        if tag in otypes: # line describes supported object type + name
          item.objectType = doc[0][1:]
          item.name = doc[1]
        elif tag in tags: # other supported tag
          if tag == 'param':    # @param inout type [name [desc]]
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
            p = JavaDocParam()
            p.sqltype = doc[1].upper()
            if len(doc)>2:
              p.name = doc[2]
              for w in range(3,len(doc)):
                p.desc += doc[w] + ' '
            item.retVals.append(p)
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
          elif tag == 'private':
            item.private = True
          elif tag == 'see':
            item.see = line[len(tag)+1:].strip()
          elif tag == 'webpage':
            item.webpage = line[len(tag)+1:].strip()
          elif tag == 'license':
            item.license = line[len(tag)+1:].strip()
        else:             # unsupported tag, ignore
          continue
        
    return res

