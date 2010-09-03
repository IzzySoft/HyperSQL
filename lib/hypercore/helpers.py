"""
HyperSQL Core helper functions
Copyright 2001 El Paso Energy, Inc.  All Rights Reserved
Copyright 2010 Itzchak Rehberg & IzzySoft
"""
__revision__ = '$Id$'

from locale import format as loc_format, setlocale, LC_NUMERIC
from iz_tools.text import * # includes import re # for eatStrings, countEmptyLines, cleanSQL
from iz_tools.system import getCallingModule # this module shall not be included in log entries ;)
from hypercore.logger import logg
logger = logg.getLogger()

# Setup gettext support
import gettext
from .gettext_init import langpath, langs
gettext.bindtextdomain('hyperjdoc', langpath)
gettext.textdomain('hyperjdoc')
lang = gettext.translation('hyperjdoc', langpath, languages=langs, fallback=True)
_ = lang.ugettext


try:
    setlocale(LC_NUMERIC, '')
except:
    None

def listCompName(a,b):
    """
    Helper to sort a list of objects by their "name" property using
    list.sort(listCompName)
    used by FileInfo.sortLists
    """
    if a.name < b.name: return -1
    elif a.name > b.name: return 1
    else: return 0

def TupleCompareFirstElements(a, b):
    """
    used for sorting list of tuples by values of first elements in the tuples
    @param tuple a
    @param tuple b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a[0] < b[0]: return -1
    if a[0] > b[0]: return 1
    return 0


def CaseInsensitiveComparison(a, b):
    """
    used for case insensitive string sorts
    @param string a
    @param string b
    @return int 0 for equal, -1 if a is less, 1 if a is greater than b
    """
    if a.upper() < b.upper(): return -1
    if a.upper() > b.upper(): return 1
    return 0

def num_format(num, places=0):
    """
    Format a number as a string
    @param number Number to format
    @param int places
    @return string formatted_number
    """
    return loc_format("%.*f", (places, num), True)

def size_format(size,decs=2):
    """
    Format file size as a string. Depending on the size, use the best fitting
    unit (B/K/M/G/T), and call num_format to care for the resulting number.
    Example: "size_format(2048,1)" would return "2.0K" on US locale ("2,0K" on German)
    @param int size Size in bytes
    @param optional int decs Decimals to use (Default: 2)
    @return string formatted_size
    """
    suffixes = [("B",2**10), ("K",2**20), ("M",2**30), ("G",2**40), ("T",2**50)]
    for suf, lim in suffixes:
        if size > lim:
            continue
        else:
            return num_format( round(size/float(lim/2**10),decs), decs )+suf


def getWordLineNr(text,word):
    """
    Wrapper to getWordLineNr from iz_tools.text catching possible errors
    @param string text Text to search IN
    @param string word WORD to search FOR
    @return list res
    """
    try:
        res = getWordLineNo(text,word)
    except:
        logger.error(_('RegExp error searching for "%s"'), word)
        res = []
    return res


def eatStrings(text):
    """
    eat (single-quoted) string contents and return remaining text.
    Keeps line count intact (multi-lined strings will be replaced by empty lines)
    @param string text text to parse
    @return string text text with strings removed
    @return boolean matched_string whether any strings where encountered
    """
    def repl(m):
        ret = '\n'*m.group(0).count('\n')
        return '\'%s\'' % ret
    strpatt = re.compile("('[^']*')+")    # String-Regexp
    text, matches = re.subn(strpatt,repl,text)
    return text, matches>0

def countEmptyLines(text):
    """
    Count lines consisting only of spaces, tabs, and formfeeds.
    @param string text Text to investigate
    @return int hits Number of empty lines (according to above specification)
    """
    patt = re.compile("(^[ \t\f\v]*$)",re.M)
    return len(patt.findall(text))

def cleanSQL(text,strings=False):
    """
    Remove comments (and optionally strings) from text
    @param mixed text Text to purge (either as string or list of strings aka lines)
    @param boolean strings Whether to remove (single-quoted) strings as well
    @return mixed text Purged text (same type as input)
    @return dict stat Some line stats: int (all,empty,comment,mixed,code), boolean matched_string
    @raise TypeError when text neither str nor list
    """
    # define some regExp patterns:
    pattIComm = re.compile('[ \t\f\v]*--.*',re.M)   # inline comment
    pattMComm = re.compile(r'\S[ \t\f\v]*--.*',re.M)# inline comment with preceding code
    pattBComm = re.compile('/\\*.*?\\*/',re.M|re.S) # block comment
    pattEnd   = re.compile('\s*\n$')                # text ending with LF

    # check input, make sure we have 'str' to process
    inputType = type(text).__name__
    if inputType   == 'list': text = ''.join(text)
    elif inputType == 'str' : pass
    else: raise TypeError('First parameter to cleanSQL must be either str or list - %s given' % inputType)

    # stats: linecount, empty, and mixed lines
    all   = text.count('\n')
    empty = countEmptyLines(text)
    mixed = len(pattMComm.findall(text))

    # we need this to fix-up stats based on '\n'
    if len(pattEnd.findall(text))>0: lf_end = True
    else: lf_end = False

    # Remove comments (and update corresponding stats)
    text  = re.sub(pattIComm,'',text)   # inline comments
    for hit in pattBComm.findall(text): # Block comments
        nlc   = hit.count('\n')
        text  = text.replace(hit,'\n'*nlc)
    comment = countEmptyLines(text) - empty
    code = text.count('\n') +1 - mixed - empty - comment

    # remove strings (if advised to do so)
    if strings:
        text, matched_string = eatStrings(text)
    else:
        matched_string = False

    # fixup stats, and make sure to return the text using the correct type
    if lf_end: empty -= 1
    else: all += 1
    if inputType == 'list': text = text.split('\n')
    return text, {'all':all, 'empty':empty, 'comment':comment, 'mixed':mixed, 'code':code, 'matched_string':matched_string}

