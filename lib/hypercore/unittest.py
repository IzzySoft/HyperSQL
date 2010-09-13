"""
$Id$
HyperSQL UnitTest
Copyright 2010 Itzchak Rehberg & IzzySoft

This module contains all neccessary functions to extract testcode information
from the @testcase Javadoc tag and produce the corresponding XML code.

The Javadoc element is defined as:
@testcase <block>

<block> can spread over multiple lines, and contains one or more of the following elements:
    name  { word };                 # name of the unit -- ONE WORD only.
    param { word text };            # var val (assignment) -- the first WORD is the name of the parameter
                                    # to pass, everything following it is the value
    basetype { word word };         # base data type for the given parameter -- first word is the
                                    # parameter name, second the base type. Useful if the original
                                    # parameter was specified with something like TABLE.COL%TYPE
                                    # but you want to tell your JUnit creator it's basically a VARCHAR
    check_param { word OP text };   # var operator value (test OUT) -- OUT param to test:
                                    # first WORD is the name of the param, second the operator,
                                    # everything following the value. OP uses only <>!=
    check_return { OP text };       # operator value (test return value of a function)
                                    # as above, just no name
    message { text };               # text returned/displayed on failure. May contain placeholders etc.
    comment { text };               # a comment on this unittest for closer description
    pre_sql { sql };                # SQL to run immediately before the test itself ("setup")
    post_sql { sql };               # SQL to run immediately after the test itself ("teardown")

One short example:
name { foobar_one };
param { foo 123 };
check_return { > 0 };
message { foo returned a negative value };
comment { Does foobar give positive results? };

With the other information extracted from the hopefully complete Javadoc of our
foobar function, we now can setup the XML:

from unittest import *
# foreach function/procedure:
  # foreach testcase: We can have multiple of them, and then just need to concat the results
    case = testcase(block)                                                    # "block" is our above block
  sig  = signature('foobar',[{'name':'foo','type':'in','datatype':'number'}]) # function foobar(foo IN NUMBER)
  xo   = xobject('function','foobar',sig,case)
suite= testsuite('function','foobar',xo)                                      # we could compile multiple suits
print unittest(suite)                                                         # outputs the XML
"""

from cgi import escape # for htmlspecialchars
from iz_tools.typecheck import is_numeric
import re

def testcase_split(block):
    """
    Takes a @testcase block and splits up its data, returning them as structured dictionary
    @param  string block
    @return dict   testcase[
              str name,
              str comment,
              str message,
              list params[ dict(str var,str val) ],
              list check [ dict(str var,str op,str val) ],
              dict ret [str op,str val] | None
            ]
    """
    # Regular expressions used to extract the information
    regElem  = re.compile('(\w+)\s*\{(.+?)\};',re.M|re.S)           # BlockElems: 'name { def };'
    regParam = re.compile('(\w+)\s*(.+)',re.M|re.S)                 # param     : 'var val'
    regCheck = re.compile('(\w+)\s*([\=\!\<\>]+)\s*(.+)',re.M|re.S) # checkParam: 'var OP val'
    retCheck = re.compile('([\=\!\<\>]+)\s*(.+)',re.M|re.S)         # return:   : 'OP val'

    # Presets
    xml = ''
    params  = []
    check   = []
    ret     = []
    basetype= []
    tc            = {}
    tc['name']    = ''
    tc['params']  = []
    tc['check']   = []
    tc['ret']     = None
    tc['message'] = ''
    tc['comment'] = ''
    tc['presql']  = None
    tc['postsql']  = None
    tc['basetypes'] = []

    # First get the elements
    elems  = regElem.findall(block) # collect all elements in (name, value) tuples
    for i in range(len(elems)):     # interprete the elements collected
        #print elems[i]
        ename = elems[i][0].lower()
        if   ename == 'name' : tc['name'] = elems[i][1].strip()
        elif ename == 'param': params.append(regParam.findall(elems[i][1]))
        elif ename in ['check','check-param','check_param','checkparam']    : check.append(regCheck.findall(elems[i][1]))
        elif ename in ['return','check-return','check_return','checkreturn']: ret = retCheck.findall(elems[i][1])
        elif ename == 'message': tc['message'] = elems[i][1].strip()
        elif ename == 'comment': tc['comment'] = elems[i][1].strip()
        elif ename in ['pre','pre_sql','presql']: tc['presql'] = elems[i][1].strip()
        elif ename in ['post','post_sql','postsql']: tc['postsql'] = elems[i][1].strip()
        elif ename == 'basetype': basetype.append(regParam.findall(elems[i][1]))
    for par in params:
        if len(par)!=1 or len(par[0])!=2: continue # must be [('var','val')]
        tc['params'].append( dict(var=par[0][0].strip(),val=par[0][1].strip()) )
    for chk in check:
        if len(chk)!=1 or len(chk[0])!=3: continue # must be [('var','op','val')]
        tc['check'].append( dict(var=chk[0][0].strip(),op=chk[0][1].strip(),val=chk[0][2].strip()) )
    for par in basetype:
        if len(par)!=1 or len(par[0])!=2: continue # must be [('var','val')]
        tc['basetypes'].append( dict(var=par[0][0].strip(),val=par[0][1].strip()) )
    if len(ret)>0:               # just if we have (at least) one, take the first
        if len(ret[0])==2:       # must be 'op val'
            tc['ret'] = dict(op=ret[0][0].strip(),val=ret[0][1].strip())
    return tc


def testcase(block):
    """
    @param  string block
    @return string xml
    Takes a @testcase block and converts it to XML
    """
    tc = testcase_split(block)                      # split up the testcase block

    if tc['ret'] is not None or len(tc['check'])>0: # if there's nothing to test we need no testunit
        xml  = '      <TESTCASE NAME="'+tc['name']+'">\n';
        if tc['comment'] != '': xml += '        <COMMENT><![CDATA['+tc['comment']+']]></COMMENT>\n'
        if tc['message'] != '': xml += '        <MESSAGE><![CDATA['+tc['message']+']]></MESSAGE>\n'
        for par in tc['params']:
            xml += '        <PARAM NAME="'+par['var']+'"><![CDATA['+par['val']+']]></PARAM>\n'
        for par in tc['basetypes']:
            xml += '        <BASETYPE NAME="'+par['var']+'" TYPE="'+par['val']+'" />\n'
        for par in tc['check']:
            xml += '        <CHECK NAME="'+par['var']+'" OP="'+par['op']+'"><![CDATA['+par['val']+']]></CHECK>\n'
        if tc['ret'] is not None:
            xml += '        <RET OP="'+tc['ret']['op']+'"><![CDATA['+tc['ret']['val']+']]></RET>\n'
        if tc['presql'] is not None:
            xml += '        <PRESQL><![CDATA['+tc['presql']+']]></PRESQL>\n'
        if tc['postsql'] is not None:
            xml += '        <POSTSQL><![CDATA['+tc['postsql']+']]></POSTSQL>\n'
        xml += '      </TESTCASE>\n'
    return xml


def signature(name,params,retval=None):
    """
    Create the XML SIGNATURE block for a function/procedure
    @param string name
    @param list   params list of dict[str name,str type,str datatype,bool optional]
    @param optional string retval datatype returned by the function
    @return string xml
    """
    xml  = '      <SIGNATURE>\n'
    xml += '        <NAME>'+name+'</NAME>\n'
    for i in range(len(params)):
        xml += '        <PARAM TYPE="'+params[i]['type']+'" DATATYPE="'+params[i]['datatype']+'" NAME="'+params[i]['name']+'" INDEX="'+str(i)+'" OPTIONAL="';
        if 'optional' in params[i] and params[i]['optional'].lower() == 'true': xml += 'TRUE'
        else: xml += 'FALSE'
        xml += '" />\n'
    if retval is not None:
        xml += '        <RET>'+retval+'</RET>\n'
    xml += '      </SIGNATURE>\n'
    return xml


def xobject(otype,oname,osig,ocase):
    """
    Glue the elements of the function/procedure together
    @param string otype object type (either 'procedure' or 'function')
    @param string oname object name
    @param string osig  objects signature (result of the signature() function)
    @param string ocase objects testcase  (result of the testcase() function).
           If there are multiple testcases, glue them together beforehand.
    """
    xml = '    <OBJECT TYPE="'+otype+'" NAME="'+oname+'">\n' \
        + osig + ocase \
        + '    </OBJECT>\n'
    return xml


def testsuite(ttype,tname,txml):
    """
    Glue the elements of a testsuite together
    @param string ttype what the testsuite is for ('package','function','procedure')
    @param string tname Name of the testsuite. This is the name of the package/function/procedure
    @param string txml  the "inner XML" of the testsuite (result of xobject();
           if multiple objects are concerned, glue them together beforehand)
    """
    xml = '  <TESTSUITE TYPE="'+ttype+'" NAME="'+tname+'">\n'\
        + txml \
        + '  </TESTSUITE>\n'
    return xml


def unittest(uxml):
    """
    Glue together the complete UnitTest XML
    @param string uxml the "inner XML" (result of testsuite()).
           If there are multiple testsuites concerned, glue them together beforehand.
    """
    return '<UNITTEST>\n'+uxml+'</UNITTEST>\n'

