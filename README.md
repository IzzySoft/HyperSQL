# HyperSQL
## Description
***HyperSQL*** is like a doxygen plus javadoc for SQL, hypermapping SQL views, packages, procedures, and functions to HTML source code listings and
showing all code locations where these are used, while some basic syntax highlighting is applied to the SQL code. The internal "where used"
functionality also scans C++ and Java source files.

***HyperSQL*** doesn't connect to any database, but rather works on files. Hence it should work for databases other than Oracle (which it was
designed for initially) as well, though I've not tested that. If you do not maintain your database objects that way (but rather develop directly
inside the database), some scripts in the `tools/` directory of the HyperSQL distribution might help you extract those from your Oracle database.
For objects you can `COMMENT ON` (tables, views) they even create basic JavaDoc comments along.

Further details as well as a documentation can be found in [the project's wiki](https://github.com/IzzySoft/HyperSQL/wiki).


## History
The original version (1.0) was written by Randy Phillips in September 2001. A customer of mine required a script like this, but some additions
were required as well. At this time, the latest release was version 1.0 from 2001, and no update was ever published since (see
[original project site](http://hypersql.sourceforge.net/)). It also looked very much like Randy abandoned the project.

So I decided to adopt the project at least temporarily (after establishing contact with Randy, he decided to hand over the project to
me completely). It was (and still is) using the GPL, so there were no problems from the license side. As said, I very much liked the idea of
***HyperSQL***, but felt it needs some polish. So on one day in February 2010, I sat down and wrote version 1.1. Versions 1.2 and 1.3 followed
the next day - and as you can see here, development still goes on (with a few breaks sometimes).

For quite a while, I was using SVN on my own server to maintain the code. But due to demand of other users who wanted to participate, I've decided to move
the code to *Github*, to make this part easier – especially as there are times I do not work myself on the project (due to lack of demand).


## Features
* flexible configuration by use of `.ini` files
* offering a lot of command line options to override configuration options on-the-fly
* generates nicely formatted HTML files, CSS adjustable by use of `.css` files
* parses SQL, C++ and Java files according to file extensions you configured
* parses Oracle Forms XML files
* generates hyperlinked listings of all objects found (SQL views, packages, functions, procedures, forms, etc.)
* hyperlinks object names to their appearance in the source code
* generates "where used" and "what used" lists, to show where your objects have been used by other objects (if they have) – helps you to find
  unused code if not, or example usages if found
* generates dependency graphs
* generates API references from JavaDoc style comments
* generates a central bug and a central todo list, compiled from all the `@bug` and `@todo` items in your JavaDoc comments
* checks validity of your JavaDoc style comments up to a certain degree, and you even may define "mandatory tags"
* generates XML for UnitTests from your JavaDoc-embedded `@testcase`s

[![Code Statistics](https://i.imgur.com/mQV7B44m.png)](https://i.imgur.com/mQV7B44.png) [![Dependency Graphs](https://i.imgur.com/54kPRzCm.png)](https://i.imgur.com/54kPRzC.png)


## License
As stated above, *HyperSQL* uses the GPLv2 license. For details, see the [License file](doc/COPYING).


## Mentions
* [HyperSQL automatically documents SQL code](https://sourceforge.net/blog/hypersql-automatically-documents-sql-code/) (SourceForge blog 7/2010)
* [Javadoc-style Documentation for PL/SQL](http://www.idmworks.com/tips-and-tricks-javadoc-style-documentation-for-plsql/) (IDMWorks Blog 9/2011)
