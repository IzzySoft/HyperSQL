"""
$Id$
HyperSQL Code Formatter
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from cgi import escape # for htmlspecialchars

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
    for line_number in range(len(line_list)):
        line  = escape(line_list[line_number])
        if line.strip()[0:2]=='--':
           text = '<SPAN CLASS="'+cssclass+'comment">' + line + '</SPAN>'
        else:
            text = line
            prel = len(text) - len(text.lstrip())
            text = text[0:prel]
            commentmode = 0 # 0 no comment, 1 '--', 2 '/*'
            for elem in line.split():
                if elem[len(elem)-1] in [',', ';', ')', '}', ']'] and len(elem)>1:
                    selem = elem[0:len(elem)-1]
                    echar  = elem[len(elem)-1]
                    if echar in [')', '}', ']']:
                        echar = '<SPAN CLASS="'+cssclass+'brace">' + echar + '</SPAN>'
                else:
                    selem = elem
                    echar  = ''
                if selem[0:1] in ['(', '{', '['] and len(selem)>1:
                    schar = '<SPAN CLASS="'+cssclass+'brace">' + selem[0:1] + '</SPAN>'
                    selem = selem[1:]
                else:
                    schar = ''
                if commentmode==0:
                    if selem[0:2]=='--':
                        text += schar + '<SPAN CLASS="'+cssclass+'comment">' + echar + selem
                        commentmode = 1
                    elif selem in keywords:
                        text += schar + '<SPAN CLASS="'+cssclass+'keyword">' + selem + '</SPAN> ' + echar
                    elif selem in types:
                        text += schar + '<SPAN CLASS="'+cssclass+'type">' + selem + '</SPAN> ' + echar
                    elif selem in ['(', ')', '[', ']', '{', '}']:
                        text += '<SPAN CLASS="'+cssclass+'brace">' + selem + echar + '</SPAN>'
                    else:
                        text += schar + selem + echar + ' '
                else: # 1 for now
                    text += ' ' + schar + selem + echar
            if commentmode==1:
                text += '</SPAN>'
            if text[len(text)-1:] != '\n':
                text += "\n"
        zeroes = (1 + line_number_width - len(`line_number`)) * "0" # leading zeroes for line numbers
        html += "<A NAME=\"" + `line_number` + "\"></A>" # hyperlink target
        html += zeroes + `line_number` + ": " + text #text
    return html
