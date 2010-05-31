"""
$Id$
Oracle Forms Parser
Copyright 2010 Itzchak Rehberg & IzzySoft

Requires the Oracle Forms modules to be converted to XML using frmf2xml

You may want to have a look at the test() function to get started.
"""

from xml.sax import saxutils, make_parser
from xml.sax.handler import feature_namespaces, ContentHandler


class FindUnits(ContentHandler):
    """
    Content handler for Oracle Forms parsing
    Requires the Oracle Forms modules to be converted to XML using frmf2xml
    """
    def __init__(self):
        self.libinfo = {}
        self.modinfo = {}
        self.units = []
        self.trigger = []

    def error(self, exception):
        """Internal: Skip over recoverable (non-fatal) errors"""
        import sys
        sys.stderr.write("\%s\n" % exception)

    def startElement(self, name, attrs):
        """Internal: Process opening tag"""
        uname = attrs.get('Name', None)
        if name == 'ObjectLibrary':                 # only present for OLB files
            libobjects = attrs.get('ObjectCount', None)
            if libobjects: libobjects = int(libobjects)
            items = attrs.items()
            self.libinfo = {'name':uname, 'objects':libobjects, 'items':items}
        elif name == 'FormModule':                  # only FMB: RealName of the module
            title = attrs.get('Title', None)
            mmod  = attrs.get('MenuModule', None)
            items = attrs.items()
            self.modinfo = {'name':uname, 'title':title, 'menumodule':mmod, 'items':items}
        elif name == 'ProgramUnit':                 # code in OLB and FMB files
            utype = attrs.get('ProgramUnitType', None)
            ucode = attrs.get('ProgramUnitText', None)
            if ucode: ucode = ucode.replace('&#10;','\n')
            self.units.append({'name':uname, 'type':utype, 'code':ucode})
        elif name == 'Trigger':                     # trigger code in OLB and FMB files
            ucode = attrs.get('TriggerText', None)
            if ucode: ucode = ucode.replace('&#10;','\n')
            self.trigger.append({'name':uname, 'code':ucode})

class OraForm:
    """
    Oracle Form Analyzer
    Requires the Oracle Forms modules to be converted to XML using frmf2xml
    Example usage:
        form = OraForm('sample_fmb.xml')
        for unit in form.getUnits(): print unit['code']
    Alternative, for processing multiple files:
        form = OraForm()
        for filename in filenames: form.setFileName(filename)
        for unit in form.getUnits(): print unit['code']
    """
    def __init__(self, filename=''):
        """ Initialize the class, optionally pass it the name of the file to process """
        if filename: self.setFileName(filename)

    def reset(self):
        """ Reset all contents for processing of a new file. If not called in between, content will be merged. """
        self.fileName = ''
        self.units    = []
        self.trigger  = []
        self.libinfo  = {}
        self.modinfo  = {}

    def setFileName(self,filename):
        """ Specify the name of the XML Form to process """
        self.reset()
        self.fileName = filename
        self.parse()

    def parse(self):
        """
        Parse the XML file and evaluate its contents. Automatically called by setFileName()
        """
        if not self.fileName: return [] # nothing to parse

        parser = make_parser()                   # Create a parser
        parser.setFeature(feature_namespaces, 0) # Tell the parser we are not interested in XML namespaces
        dh = FindUnits()                         # Create the handler
        parser.setContentHandler(dh)             # Tell the parser to use our handler
        parser.parse(self.fileName)              # Parse the input
        self.units   = dh.units
        self.trigger = dh.trigger
        self.libinfo = dh.libinfo
        self.modinfo = dh.modinfo

    def getUnits(self):
        """
        Return the ProgramUnits details of the processed form
        @return list units list of dicts (name, type, code)
        """
        return self.units

    def getModuleName(self):
        """
        Return the name of the module. This is either the "FormModule" name (for
        FMB), or the object library name (for OLB)
        @return string name
        """
        if len(self.modinfo): return self.modinfo['name']
        elif len(self.libinfo): return self.libinfo['name']
        else: return None

    def getModuleInfo(self):
        """
        Return general info about the module (for FMB files, otherwise empty)
        @return dict modinfo (str name, str title, str menumodule, list items (tuple str name, str val))
        """
        return self.modinfo

    def getLibraryName(self):
        """ alias for getModuleName """
        return self.getModuleName()

    def getLibraryInfo(self):
        """
        Return general info about the library (for OLB files, otherwise empty)
        @return dict libinfo (name, objects, list items (tuple str name, str val)) -
                where objects is the object count
        """
        return self.libinfo

    def getTrigger(self):
        """
        Return the Trigger details of the processed form
        @return list trigger list of dicts (name, code)
        """
        return self.trigger

def test(filename,printcode=False):
    """
    Simple test unit to a) test if everything works and/or b) show what kind of
    information is extracted (to get you started)
    @param string filename name of the XML file representing the form to process
    @param optional boolean printcode Whether to printout code contents (may get very verbose!). Default: False
    """
    form = OraForm(filename)
    units = form.getUnits()
    trigger = form.getTrigger()
    libinfo = form.getLibraryInfo()
    modinfo = form.getModuleInfo()
    if (modinfo):
        print 'Module ' + modinfo['name']
        print '=' * len('Module ' + modinfo['name'])
        print 'ModuleInfo: ' + `modinfo`
    if (libinfo):
        print 'Library ' + libinfo['name']
        print '=' * len('Library ' + libinfo['name'])
        print 'LibraryInfo: ' + `libinfo`
    print `len(units)` + ' code units identified:'
    for i in range(len(units)):
        utype = units[i]['type'] or '<Deleted Object>'
        uname = units[i]['name'] or '<NoName>'
        print '* ' + utype + ' ' + uname
        if printcode:
            code = units[i]['code'] or ''
            print '-' * len('* ' + utype + ' ' + uname)
            print code
            print ''
    print `len(trigger)` + ' trigger units identified:'
    for i in range(len(trigger)):
        uname = trigger[i]['name'] or '<NoName>'
        print '* ' + uname
        if printcode:
            ucode = trigger[i]['code'] or ''
            print '-' * len('* ' + uname)
            print ucode
            print ''
