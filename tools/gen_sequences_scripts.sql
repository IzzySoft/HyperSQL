--
-- there are no comments on sequences, so we simply extract the CREATE statements
--

SET ECHO OFF
SET FEEDBACK OFF
SET SERVEROUT ON
SET SQLBL ON
SET TERMOUT ON
SET PAGES 0
SET LINES 200
SET SERVEROUT ON

SPOOL sequences.sql
SELECT 'CREATE SEQUENCE '||i.sequence_name||' START WITH '||i.min_value||' INCREMENT BY '||i.increment_by
     ||' MAX VALUE '||i.max_value||i.caches||i.cycles||i.orders||';' AS line
  FROM (
        SELECT sequence_name,min_value,increment_by,max_value,
              (CASE WHEN cache_size=0 THEN ' NOCACHE' ELSE ' CACHE '||cache_size END) AS caches,
              (CASE WHEN cycle_flag='Y' THEN ' CYCLE' ELSE ' NOCYCLE' END) AS cycles,
              (CASE WHEN order_flag='Y' THEN ' ORDER' ELSE ' NOORDER' END) AS orders
          FROM user_sequences
       ) i;
SPOOL OFF

EXIT;
