/**
 * Extract table definitions from data dictionary
 * As preparation, you will need an Oracle DIRECTORY to place the created
 * scripts into:
 * DROP DIRECTORY UTLFILEDIR;
 * CREATE OR REPLACE DIRECTORY UTLFILEDIR AS '</path/to/store/output>';
 * GRANT READ, WRITE ON DIRECTORY UTLFILEDIR TO <schema_owner>;
 * Replace <path> and <schema_owner> to match your needs. If you change the name
 * of the directory, you will need to do so in below script as well.
 */

SET ECHO OFF
SET FEEDBACK OFF
SET SERVEROUT ON
SET SQLBL ON
SET TERMOUT ON
SET PAGES 0
SET LINES 200

DECLARE
  cnt NUMBER; -- in case we want a range only
  fh UTL_FILE.FILE_TYPE;
  fname VARCHAR2(255); 
  CURSOR c_tab IS
    SELECT table_name
      FROM user_tables;
  CURSOR c_tabcomment(tname IN VARCHAR2) IS
    SELECT '/** '||comments AS line
      FROM user_tab_comments
     WHERE table_name = tname;
  CURSOR c_colcomment(tname IN VARCHAR2) IS
    SELECT ' * @col '||t.data_type||' '||t.column_name||' '||c.comments AS line
      FROM user_tab_columns t LEFT JOIN user_col_comments c ON (t.table_name=c.table_name AND t.column_name=c.column_name)
     WHERE t.table_name=tname;
  CURSOR c_grant(tname IN VARCHAR2) IS
    SELECT (CASE WHEN grantable='NO' THEN 'GRANT '||privilege||' ON '||tname||' TO '||grantee||';'
           ELSE  'GRANT '||privilege||' ON '||tname||' TO '||grantee||' WITH GRANT OPTION;' END) AS line
      FROM user_tab_privs
     WHERE table_name=tname;
BEGIN
  dbms_metadata.set_transform_param(dbms_metadata.session_transform,'EMIT_SCHEMA',false); -- undocumented: remove schema
  dbms_metadata.set_transform_param(dbms_metadata.session_transform,'CONSTRAINTS_AS_ALTER',true); -- let's have them separate
  dbms_metadata.set_transform_param (dbms_metadata.session_transform, 'SEGMENT_ATTRIBUTES', false); -- skip nasty defaults
  dbms_metadata.set_transform_param (dbms_metadata.session_transform, 'SQLTERMINATOR', true); -- end each statement with ';'
  dbms_metadata.set_transform_param (dbms_metadata.session_transform, 'PRETTY', true); -- not sure what gets prettier here
  cnt := 0;
  FOR rec IN c_tab LOOP
    cnt := cnt +1;
    IF cnt < 1 THEN
      CONTINUE;
    END IF;
    fname := lower(rec.table_name)||'.sql';
    fh := utl_file.fopen('UTLFILEDIR',fname,'W',32767);
    FOR r1 IN c_tabcomment(rec.table_name) LOOP
      utl_file.put_line(fh,r1.line);
    END LOOP;
    utl_file.put_line(fh,' * @table '||rec.table_name);
    FOR r1 IN c_colcomment(rec.table_name) LOOP
      utl_file.put_line(fh,r1.line);
    END LOOP;
    utl_file.put_line(fh,' */');
    utl_file.putf(fh,dbms_metadata.get_ddl( object_type => 'TABLE' , name => rec.table_name)||'\n');
    BEGIN
      utl_file.putf(fh,dbms_metadata.get_dependent_ddl('COMMENT',rec.table_name)||'\n');
    EXCEPTION
      WHEN OTHERS THEN NULL; -- no comments found
    END;
    FOR r1 IN c_grant(rec.table_name) LOOP
      utl_file.put_line(fh,r1.line);
    END LOOP;
    utl_file.fclose(fh);
--    exit;
  END LOOP;
  EXCEPTION
    WHEN utl_file.invalid_path THEN raise_application_error(-20000, 'ERROR: Invalid PATH FOR file.');
END;
/

EXIT;
