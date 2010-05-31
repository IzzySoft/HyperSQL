#!/bin/bash

#  DESCRIPTION
#    This file is used to call the Forms2XML conversion tool.
#    It takes .fmb, .mmb, and .olb files and converts them into XML.
# 
#  NOTES
#    It wraps the class oracle.forms.util.xmltools.Forms2XML and passes
#    any parameters given onto the tool.
#    You can only use the standard nine parameters, but these can include
#    wildcards in the filenames.
#

# Test whether the DISPLAY is set (JDAPI needs that :-( )
[ -z "$DISPLAY" ] && {
  echo "You must have a valid DISPLAY variable set up to use this script."
  exit 1
}

# Setup environment incl. the path to include the necessary Forms dlls.
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/jdk/bin$PATH
export CLASSPATH=$ORACLE_HOME/jre:$ORACLE_HOME/jlib:$ORACLE_HOME/network/jlib
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$ORACLE_HOME/jdk/jre/lib/i386/server:$ORACLE_HOME/jdk/jre/lib/i386/native_threads:$ORACLE_HOME/jdk/jre/lib/i386:$LD_LIBRARY_PATH
export ORACLE_TERM=vt220
export O_JDK_HOME=${O_JDK_HOME:-/igweb/iAS10gR2/jdk}
export FORMS_PATH=${FORMS_PATH}:$ORACLE_HOME/forms
export FORMS_API_TK_BYPASS=TRUE

# Run the tool with the required jar files added to the classpath
$ORACLE_HOME/jdk/bin/java -classpath $ORACLE_HOME/forms/java/frmxmltools.jar:$ORACLE_HOME/forms/java/frmjdapi.jar:$ORACLE_HOME/lib/xmlparserv2.jar:$ORACLE_HOME/lib/xschema.jar oracle.forms.util.xmltools.Forms2XML $*
