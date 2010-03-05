"""
$Id$
IniParser - an extention to ConfigParser
Copyright 2010 Itzchak Rehberg & IzzySoft
"""

from ConfigParser import ConfigParser
from sys import stderr

class IniParser(ConfigParser):
    """
    An extension to ConfigParser, adding a getList() method to the class -
    plus a Default parameter to option retrieval. Using the latter, it also
    tries to (silently) bypass ValueError exceptions (see logMode).
    As for the defaults which may be passed to ConfigParser.__init__,
    they cannot be assigned to a specific section - so if the same keyword
    exists in multiple sections, those defaults are useless. To bypass this
    limit, you can either pass above mentioned defaults for option retrieval -
    or specify section specific defaults using the IniParser.setVals() method.
    """
    def __init__(self,defaults=None):
        """
        Initialize the instance
        @param self
        @param defaults A dictionary of intrinsic defaults. The keys must be
               strings, the values must be appropriate for %()s string
               interpolation.  Note that `__name__' is always an intrinsic
               default; it's value is the section's name. These defaults are
               not section specific.
        """
        ConfigParser.__init__(self,defaults)
        self.logMode = stderr

    def setVals(self,vals):
        """
        Setting multiple configuration values from a passed dictionary.
        This can either be used to initialize the configuration with useful
        defaults (section specific - not global as the constructor does) -
        or to overwrite settings at a later point (e.g. after parsing additional
        command line options).
        @param self
        @param defaults dictionary with the structure defaults[section][option]=string
        ATTENTION: Keep in mind: Already existing options will be overwritten by
        values from the passed dict!
        """
        if type(vals).__name__ == 'dict':
            for sect in vals.iterkeys():
                if not self.has_section(sect):
                    self.add_section(sect)
                for opt in vals[sect].iterkeys():
                    self.set(sect,opt,vals[sect][opt])

    def setLogMode(self,mode):
        """
        If some errors occur (e.g. due to invalid values specified), IniParser
        tries to silently fix this. For example, if you try to retrieve the value
        'dummy' as integer, this normally would rise an exeption - so if you
        passed a default value to getInt, IniParser this and only raises an
        exeption otherwise. Though, you might want to inform the user - which will
        be done if you set the logMode correspondingly
        @param self
        @param mode logMode to set: None to keep quite, 'stderr' for error output (default)
        """
        if mode in ['None','stderr']:
            self.logMode = mode

    def log(self,msg):
        """
        Print an error message to the output specified by setLogMode()
        @param self
        @param msg message to print
        """
        if self.logMode != 'None':
            print >>stderr, '! '+msg

    def get(self,sect,opt,default=None):
        """
        Get an option from the config as string
        @param self
        @param string section name
        @param string option name
        @param optional string default value (default: None)
        @return string value
        """
        try:
          if self.has_option(sect,opt):
            return ConfigParser.get(self,sect,opt)
          else:
            return default
        except ValueError:
          if default != None:
            self.log('An invalid value was specified for '+sect+'.'+opt)
            return default
          else:
            raise ValueError('An invalid value was specified for '+sect+'.'+opt)

    def getList(self,sect,opt,default=None):
        """
        Get an option from the config as list
        @param self
        @param string section name
        @param string option name
        @param optional list default value (default: None)
        @return list value
        """
        if self.has_option(sect,opt):
          return ConfigParser.get(self,sect,opt).split(' ')
        else:
          return default

    def getBool(self,sect,opt,default=None):
        """
        Get an option from the config as boolean value
        @param self
        @param string section name
        @param string option name
        @param optional boolean default value (default: None)
        @return boolean value
        """
        try:
          if self.has_option(sect,opt):
            return self.getboolean(sect,opt)
          else:
            return default
        except ValueError:
          msg = 'invalid value for '+sect+'.'+opt+' - "'+self.get(sect,opt)+'" cannot be translated into a boolean.'
          if default != None:
            self.log(msg)
            return default
          else:
            raise ValueError(msg)

    def getInt(self,sect,opt,default=None):
        """
        Get an option from the config as integer value
        @param self
        @param string section name
        @param string option name
        @param optional int default value (default: None)
        @return int value
        """
        try:
          if self.has_option(sect,opt):
            return self.getint(sect,opt)
          else:
            return default
        except ValueError:
          msg = 'invalid value for '+sect+'.'+opt+' - "'+self.get(sect,opt)+'" cannot be translated into an integer.'
          if default != None:
            self.log(msg)
            return default
          else:
            raise ValueError(msg)

    def getFloat(self,sect,opt,default=None):
        """
        Get an option from the config as float value
        @param self
        @param string section name
        @param string option name
        @param optional float default value (default: None)
        @return float value
        """
        try:
          if self.has_option(sect,opt):
            return self.getfloat(sect,opt)
          else:
            return default
        except ValueError:
          msg = 'invalid value for '+sect+'.'+opt+' - "'+self.get(sect,opt)+'" cannot be translated into a float.'
          if default != None:
            self.log(msg)
            return default
          else:
            raise ValueError(msg)
