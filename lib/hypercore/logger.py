"""
Provide logging for all modules
Automatically creates an instance of our Logger class - so basically only
logg needs to be imported from here. Of course, the first time the configuration
has to take place (logg.setScreenLog() and logg.setFileLog()) - afterwards only
logg.getLogger() will be needed when a logger shall be used.
"""
__revision__ = '$Id$'

import logging

class Logger(object):
    """
    Handles Logger stuff for the entire app
    """
    def __init__(self):
        """
        Very basic initialization of a root logger
        """
        self.logger = logging.getLogger();
        self.logger.setLevel(logging.DEBUG)
        logging.addLevelName(99,'NONE')
        self.ch  = logging.StreamHandler() # screen logging handler
        self.fh  = None                    # file logging handler
        #logging.captureWarnings = False   # introduced with Python 2.7, False is already default

    def captureWarnings(self,capture=False):
        """
        Enable/Disable capture of Python warnings to the logger. As this feature
        was introduced with Python v2.7, this method will do nothing if a lower
        version of Python is calling it.
        @param optional boolean capture (default: False)
        """
        if sys.hexversion > 0x02070000:
            logging.captureWarnings(captureWarnings)

    def setScreenLog(self,level):
        """
        Setup screen logging. This adds the corresponding logging channel, and
        sets its log level and formatting.
        @param string level Defines the verbosity. Accepts the levels defined
               by the logging package, plus 'NONE' to switch it off. If an
               invalid level was specified, it falls back to 'ERROR'.
               This is case insensitive (will be converted to upper())
        """
        #ch.setFormatter( logging.Formatter("* %(name)s %(levelname)s %(message)s") )
        self.ch.setFormatter( logging.Formatter("* %(name)-12s %(levelname)-8s %(message)s") )
        try:
            self.ch.setLevel( logging.__getattribute__(level.upper()) )
        except AttributeError:
            self.ch.setLevel(logging.ERROR)
        self.logger.addHandler(self.ch)

    def setFileLog(self,level,fname,encoding='ascii',maxbytes=0,backupCount=3):
        """
        Setup file logging. This adds the corresponding logging channel, and
        sets its log level, formatting, etc.
        @param string level Defines the verbosity (see setScreenLog for details)
        @param string fname Name of the log file (w/ path)
        @param optional string encoding Encoding to use. Defaults to 'ascii'
        @param optional integer maxbytes If this is != 0, it enables automatic
               log rotation to take place at the given size
        @param optional integer backupCount How many copies to keep on log
               rotation (default: 3). Has no effect with maxbytes=0 (obviously).
        """
        if maxbytes==0:
            self.fh = logging.FileHandler( fname, 'a', encoding )
        else:
            from logging.handlers import RotatingFileHandler
            self.fh = RotatingFileHandler(
              fname, 'a',
              maxbytes, backupCount,
              encoding
            )
        #fh.setFormatter( logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s") )
        self.fh.setFormatter( logging.Formatter("%(asctime)s %(name)-10s %(levelname)-8s %(message)s") )
        try:
            self.fh.setLevel( logging.__getattribute__(level.upper()) )
        except AttributeError:
            self.fh.setLevel(logging.WARNING)
        self.logger.addHandler(self.fh)

    def getLogger(self,lname='HyperSQL'):
        """
        Obtain a logger instance
        @param optional string lname Name of the logger instance to return (Default: 'HyperSQL')
        @return object logger Instance of logging.Logger
        """
        return logging.getLogger(lname)

logg = Logger()
