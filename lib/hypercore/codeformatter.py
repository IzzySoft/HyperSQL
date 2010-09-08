"""
$Id$
HyperSQL Code Formatter
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from cgi import escape # for htmlspecialchars
from iz_tools.typecheck import is_numeric
import re

def hypercode(line_list,keywords,types,cssclass='sql'):
    """
    Format (SQL) code passed by the line_list parameter. Nothing is prepended
    or appended (so no opening CODE tag or the like).
    As the lists of keywords and types are passed to this function, all kind
    of code could be highlighted passing the corresponding lists.
    @param list line_list List of code lines
    @param list keywords keywords to highlight
    @param list types types to highlight
    @param string cssclass prefix for the CSS-classes to use. Defaults to 'sql'.
            Used classes (taking the SQL as example) are: 'sqlcomment' for comments,
            'sqlbrace' for opening parenthesis, 'sqlkeyword' for keywords, and
            'sqltype' for types.
    Returns: html_string HTML formatted code
    """

    # we need leading zeroes for the line numbers
    line_number_width = len(`len(line_list)`) # number of chars in "number of lines of text"

    html = ''
    commentmode = 0 # 0 no comment, 1 '--', 2 '/*', 3 in_singlequote_string
    splitter = re.compile('([\'\s,\.;\:%\(\)\}\{\|\<\>])')
    for line_number in range(len(line_list)):
        line  = escape(line_list[line_number]).replace('&lt;','<').replace('&gt;','>')
        if line.strip()[0:2]=='--':
           text = '<SPAN CLASS="'+cssclass+'comment">' + line + '</SPAN>'
        else:
            text = ''
            if commentmode==2:
                text += '<SPAN CLASS="'+cssclass+'comment">'
            oldelem = ''
            tokens = splitter.split(line)
            for idx in range(len(tokens)):
                elem = tokens[idx]
                if commentmode==0:
                    if elem[0:2]=='--':
                        text += '<SPAN CLASS="'+cssclass+'comment">' + elem
                        commentmode = 1
                    elif elem[0:2]=='/*':
                        text += '<SPAN CLASS="'+cssclass+'comment">' + elem
                        commentmode = 2
                    elif elem=="'":
                        text += '<SPAN CLASS="'+cssclass+'brace">\'</SPAN><SPAN CLASS="'+cssclass+'string">'
                        commentmode = 3
                    elif elem[0:1]=="'":
                        text += '<SPAN CLASS="'+cssclass+'brace">\'</SPAN><SPAN CLASS="'+cssclass+'string">' + elem[1:len(elem)-1]
                        if elem[len(elem)-1:]=="'":
                            text += '</SPAN><SPAN CLASS="'+cssclass+'brace">\'</SPAN>'
                        else:
                            text += elem[len(elem)-1:]
                            commentmode = 3
                    elif elem in [',', ':', '=', '(', ')', '[', ']', '{', '}'] \
                      or (elem==';' and (len(oldelem)==0 or oldelem[0]!='&')): # skip html entities for ;
                        text += '<SPAN CLASS="'+cssclass+'brace">' + elem + '</SPAN>'
                    elif elem in ['<','>']:
                        text += '<SPAN CLASS="'+cssclass+'brace">' + escape(elem) + '</SPAN>'
                    elif is_numeric(elem):
                        text += '<SPAN CLASS="'+cssclass+'numeric">' + elem + '</SPAN>'
                    elif elem in keywords:
                        text += '<SPAN CLASS="'+cssclass+'keyword">' + elem + '</SPAN>'
                    elif elem in types:
                        text += '<SPAN CLASS="'+cssclass+'type">' + elem + '</SPAN>'
                    else: text += elem
                elif commentmode==2:
                    if elem[len(elem)-2:]=='*/':
                        text += escape(elem) + '</SPAN>'
                        commentmode = 0 # clear at comment end
                    else: text += escape(elem)
                elif commentmode==3:
                    if elem=="'":
                        if not ( idx>0 and tokens[idx-1]=="'" ) or ( len(tokens)>idx and tokens[idx+1]=="'" ):
                            text += '</SPAN><SPAN CLASS="'+cssclass+'brace">\'</SPAN>'
                            commentmode = 0
                    else: text += escape(elem)
                else: # 1 for now
                    text += escape(elem)
                oldelem = elem # remember for back-check
            if commentmode==1:
                text += '</SPAN>'
                commentmode = 0 # clear at line end
            elif commentmode==2:
                text += '</SPAN>'
            #if text[len(text)-1:] != '\n':
            #    text += "\n"
        text = text.replace('\n\n','\n')
        zeroes = (1 + line_number_width - len(`line_number+1`)) * "0" # leading zeroes for line numbers (+1 since we start with 0)
        html += "<A NAME=\"L" + `line_number+1` + "\"></A>" # hyperlink target
        html += zeroes + `line_number+1` + ": " + text #text
    return html
