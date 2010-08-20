#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    $Id$

    HyperSQL PL/SQL UnitTest Generator Demo

    This is just a demonstration of the usage of XML UnitTest definition
    files exported by HyperSQL. If you call this script and pass it the
    name of such an XML file, it will generate PL/SQL unit-tests from it
    and print the PL/SQL code to STDOUT. So you could e.g. use it like:

    for file in *.xml; do ./ut_plsql.py $file > ${file%*.xml}.sql; done

    to loop over all XML files in the current directory.

    Please understand that this is just "proof of concept" code. It seems to
    work for simple things, but nothing's guaranteed. Feel free to modify
    and improve, or use it as inspiration to write your own generator. If you
    then want it to be included with HyperSQL, or have it mentioned with its
    documentation and/or web site, drop a note to the author who will be
    happy to read about this ;)

    Copyright 2010 Itzchak Rehberg & IzzySoft

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    Author contact information:
       izzysoft AT qumran DOT org

"""

from xml.etree.ElementTree import parse
from sys import argv

#------------------------------------------------------------------------------
def getSuites(fname):
    """
    Extract the unit test suites from a given XML file
    @param  string fname  name of the XML file
    @return list   suites list of test-suites
        - Each element of this list is a dictionary holding the 'name' of the
          suite (str), its 'type' (str, either 'package' or 'standalone'), and
          all contained 'objects' (list of functions/procedures we have
          test-cases for).
        - Each object again is a dictionary with its 'name' (str), 'type' (str;
          either 'function' or 'procedure'), its 'signature' (dict), and 'tests'
          (list of test-cases).
        - A signature consists of the objects 'name' (str), 'params' (list), and
          a 'return' datatype (str - for procedures, this is None)
        - A test (case) has a 'name' (str), a 'comment' (str), a 'message' (str)
          to display in case of errors, 'params' (list) to be passed to the object,
          a 'return' (dict for functions, otherwise None) condition, and 0 or more
          OUT parameters to 'check' (list).
        - A signature param has a 'name' (str), a 'type' (str in|out|inout), a
          'datatype' (str; e.g. 'NUMBER'), an 'index' (int) telling its position,
          and it tells us whether this parameter is 'optional' (str TRUE|FALSE).
        - A test (case) param tells us what to pass to the function/procedure.
          It consists of str 'var' and str 'val'.
        - A test case 'return' tells us what we expect a function to return (as
          a procedure has no such feature, 'return' is always None here). Thus
          it holds an operator (str 'op', e.g. '=') and a value (str 'val').
        - A test (case) 'check' parameter informs about expected OUT values, so
          here we have the name of the parameter (str 'var'), the operator (str
          'op'), plus the value (str 'val') to compare with.
    """
    et   = parse( open(fname,'rb') )
    root = et.getroot()

    suites = [] # the XML file may hold one or more TESTSUITES

    for suite in root:                              # Walk the TESTSUITE elements
        s = {}
        s['name']    = suite.attrib['NAME'].strip()
        s['type']    = suite.attrib['TYPE'].strip()
        s['objects'] = []

        for obj in suite:                           # Parse the contained functions/procedures
            o = {}
            o['name'] = obj.attrib['NAME'].strip()
            o['type'] = obj.attrib['TYPE'].strip()

            sig = obj.find('SIGNATURE')             # obtain the objects signature
            o['signature'] = {}
            o['signature']['name'] = sig.findtext('NAME').strip()
            o['signature']['params'] = []
            try:
                o['signature']['return'] = sig.findtext('RET').strip()
            except:
                o['signature']['return'] = None
            for par in sig.findall('PARAM'):
                p = {}
                p['type'] = par.attrib['TYPE'].strip()
                p['name'] = par.attrib['NAME'].strip()
                p['datatype'] = par.attrib['DATATYPE'].strip()
                p['index']    = int(par.attrib['INDEX'].strip())
                p['optional'] = par.attrib['OPTIONAL'].strip()
                o['signature']['params'].append(p)

            o['tests'] = []
            for etc in obj.findall('TESTCASE'):      # Now collect the test-cases
                tc = {}
                tc['name'] = etc.attrib['NAME'].strip()
                tc['comment'] = ( etc.findtext('COMMENT') or '' ).strip()
                tc['message'] = ( etc.findtext('MESSAGE') or '' ).strip()
                ret = etc.find('RET')
                if ret is None: tc['return'] = None
                else: tc['return'] = dict(op=ret.attrib['OP'],val=ret.text)
                tc['check'] = []
                for par in etc.findall('CHECK'):
                    tc['check'].append( dict(var=par.attrib['NAME'],op=par.attrib['OP'],val=par.text) )
                tc['params'] = []
                for par in etc.findall('PARAM'):
                    tc['params'].append( dict(var=par.attrib['NAME'],val=par.text) )
                o['tests'].append(tc)

            s['objects'].append(o)

        suites.append(s)

    return suites


#------------------------------------------------------------------------------
# Define our default messages
reporting_sql = """
  --
  -- Helpers to report our UnitTest results
  --
  success NUMBER := 0;
  failed  NUMBER := 0;
  errors  NUMBER := 0;
  deferr  NUMBER := 0;
  PROCEDURE report_unit_start(name IN VARCHAR2) IS
    BEGIN
        dbms_output.put_line('UNITTEST START FOR '||name);
    END report_unit_start;
  PROCEDURE report_unit_end(name IN VARCHAR2) IS
    BEGIN
        dbms_output.put_line('RESULTS FOR UNITTEST '||name||': ');
        dbms_output.put_line('Definition errors: '||deferr||', Errors: '||errors||', Failed: '||failed||', OK: '||success);
    END report_unit_end;
  PROCEDURE report_definition_error (obj IN VARCHAR2, msg IN VARCHAR2 DEFAULT '') IS
    BEGIN
        dbms_output.put_line('"'||obj||'" could not been tested due to invalid test specification.');
        IF msg != '' THEN
            dbms_output.put_line('Details: '||msg);
        END IF;
        deferr := deferr +1;
    END report_definition_error;
  PROCEDURE report_failure (obj IN VARCHAR2, msg IN VARCHAR2 DEFAULT '') IS
    BEGIN
        IF msg = '' THEN
            dbms_output.put_line('UnitTest for '||obj||' failed.');
        ELSE
            dbms_output.put_line(obj||': '||msg);
        END IF;
        failed := failed +1;
    END report_failure;
  PROCEDURE report_error (obj IN VARCHAR2,sqlerr IN VARCHAR2) IS
    BEGIN
        dbms_output.put_line('An error occured while testing "'||obj||'":');
        dbms_output.put_line(sqlerr);
        errors := errors +1;
    END report_error;
  PROCEDURE report_success(obj IN VARCHAR2) IS
    BEGIN
        success := success +1;
    END report_success;

  --
  -- The UnitTests themselves
  --
"""

#------------------------------------------------------------------------------
def makePackage(suite,prefix='test_'):
    """
    Generate a test package for the suite passed.
    We usually want one package per test-suite (and one test-suite per package).
    @param dict suite test-suite to process. This is one element of the list
           returned by getSuites().
    @param optional string prefix prefix for the name of the generated package.
           This will prepended to the suites name, which usually is the name of
           the package the test-suite is generated for.
    @return string sql SQL text containing the code to create the package spec
            and body in your database.
    """
    if not suite: return

    pkgname = prefix+suite['name']
    if len(pkgname)>30: pkgname = pkgname[:30]

    numbertypes = ['number','integer']
    intro = '-- ------------------------------------------------------------------\n' \
          + '-- Testsuite '+suite['name']+'\n' \
          + '-- ------------------------------------------------------------------\n\n'

    def fixDBType(dbtype):
        """
        In the DEFINE section, Oracle does not like e.g. VARCHAR2 without its
        length specified. Here we fix those things up, giving them the max possible
        @param  string dbtype e.g. 'VARCHAR2', 'NUMBER', ...
        @return string dbtype e.g. 'VARCHAR2(4000)', 'NUMBER', ...
        """
        if dbtype.lower() in ['varchar','varchar2']: return 'VARCHAR2(4000)'
        else: return dbtype.upper()

    def fullObjName(suite,obj):
        """
        Get the name to call an object. For stand-alone functions/procedures,
        this is simply the object name - but for packages, it must be preceded
        by the package name to be found
        @param dict suite the suite containing this object
        @param dict obj   the object itself
        """
        if suite['type'].lower() == 'package': return suite['name']+'.'+obj['name']
        else: return obj['name']

    def getParVal(name,tc):
        """
        Retrieve the value to pass for a parameter from the testcase
        @param string name Name of the parameter
        @param dict   tc   Test-case
        """
        for par in tc['params']:
            if par['var'].lower() == name.lower(): return par['val']
        return None

    def getParDataType(name,params):
        for par in params:
            if name==par['name']: return par['datatype']
        return None

    spec = 'CREATE OR REPLACE PACKAGE '+pkgname+' AS\n' \
         + '  PROCEDURE '+prefix+'run_all;\n'
    body = 'CREATE OR REPLACE PACKAGE BODY '+pkgname+' AS\n' + reporting_sql
    runall = "  PROCEDURE "+prefix+"run_all IS\n    BEGIN\n      report_unit_start('"+suite['name']+"');\n"

    for obj in suite['objects']:
        # First check the signature
        if obj['type'].lower()=='function':
            if obj['signature']['return'] is None:
                runall +=  "      report_definition_error('function "+fullObjName(suite,obj)+"','Missing return value');\n"
                continue;
        else:
            if obj['signature']['return'] is not None:
                runall += "      report_definition_error('procedure "+fullObjName(suite,obj)+"','return value specified for a procedure');\n"
                continue;

        # Still here - so the signature was OK. Now setup the test-cases:
        cnum = 0 # testcase number, in case we have no name
        for tc in obj['tests']:

            # Make sure we have all params needed
            pars = []
            for i in range(len(obj['signature']['params'])): pars.append(None) # so we can assign by index now
            for param in obj['signature']['params']:
                if param['type'].lower() in ['in','inout']:
                    val = getParVal(param['name'],tc)
                    if val is None: # not defined!
                        runnall += "      report_definition_error('function "+fullObjName(suite,obj)+"','Missing value for parameter "+param['name']+"');\n"
                        continue;
                else: # just some OUT parameter, so nothing to pass to it
                    val = None
                pars[param['index']] = dict(name=param['name'],datatype=param['datatype'],value=val)
            if obj['type'].lower()=='function' and tc['return'] is None:
                runall += "      report_definition_error('function "+fullObjName(suite,obj)+"','Missing return value');\n"

            # Now setup the testcase procedure
            pname = (tc['name'] or obj['name']+`cnum`)
            if len(pname)>30: pname = pname[:(30-len(`cnum`))]+`cnum`
            spec   += '  PROCEDURE '+pname+';\n'
            runall += '      '+pname+'();\n'
            body   += '  PROCEDURE '+pname+' IS\n'
            if obj['type'].lower()=='function':
                body += '    retval '+fixDBType(obj['signature']['return'])+';\n'
                tcall = '    retval := '+fullObjName(suite,obj)+'('
            else:
                tcall = '    '+fullObjName(suite,obj)+'('

            for i in range(len(pars)): # construct the call parameters
                body  += '    '+pars[i]['name']+' '+fixDBType(pars[i]['datatype'])
                if pars[i]['value'] is not None:
                    body += ' := '
                    if pars[i]['datatype'].lower()=='number': body += pars[i]['value']
                    else: body += "'"+pars[i]['value']+"'"
                body += ';\n'
                if i > 0: tcall += ','
                tcall += pars[i]['name']

            tcall += ');\n'
            body  += '    BEGIN\n  '+tcall

            if obj['type'].lower() == 'function': # check return value
                body += '      IF retval '
                if tc['return']['val']=='NULL':
                    if tc['return']['op']=='=': body += 'IS NULL THEN\n'
                    else:                       body += 'IS NOT NULL THEN\n'
                else:
                    body += tc['return']['op']+' '
                    if obj['signature']['return'].lower() in numbertypes: body += tc['return']['val']
                    else: body += "'"+tc['return']['val']+"'"
                    body += ' THEN\n'
                body += "        NULL;\n" \
                     +  '      ELSE\n' \
                     +  "        report_failure('"+pname+"','"+(tc['message'] or 'wrong return value')+"');\n" \
                     +  '        RETURN;\n' \
                     +  '      END IF;\n'

            for param in tc['check']: # check OUT params
                body += '      IF '+param['var']+' '
                if param['val']=='NULL':
                    if param['op']=='=': body += 'IS NULL THEN\n'
                    else               : body += 'IS NOT NULL THEN\n'
                else:
                    body += param['op']+' '
                    if getParDataType(param['var'],obj['signature']['params']) in numbertypes:
                        body += param['val']+' THEN\n'
                    else:
                        body += "'"+param['val']+"' THEN\n"
                body += '        NULL;\n' \
                     +  '      ELSE\n' \
                     +  "        report_failure('"+pname+"','"+(tc['message'] or 'wrong OUT value for parameter '+param['var'])+"');\n" \
                     +  '        RETURN;\n' \
                     +  '      END IF;\n'
            body += "      report_success('"+pname+"');\n" \
                 +  '    END '+pname+';\n'
            cnum  += 1

    runall += "      report_unit_end('"+suite['name']+"');\n"
    spec += 'END '+pkgname+';\n/\n\n'
    body += runall+'    END '+prefix+'run_all;\nEND '+pkgname+';\n'

    return intro+spec+body+'/\n'


#------------------------------------------------------------------------------
if __name__ == "__main__":
    suites = getSuites(argv[1])
    for suite in suites:
        sql = makePackage(suite)
        print sql

