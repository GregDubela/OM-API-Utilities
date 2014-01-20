OM-API-Utilities
================

A few python utilities for managing list Creation and users in OpenMinds, via its API 

All of these Python files work in a very similar fashion:

1. They first establish credentials using the OM API functions. 
2. Once the credentials are established, they will attempt some OM task such as List Creation.


### This Repo has files that Perform 3 different sets of tasks.

Task 1: Create OM Lists (from csv files or a directory full of csv files)
This is most probably what you want to do.

Task 2: Specialized Py routines to create Jeopardy Lists For OM.
Those files are contained in `JeopardyParser`

Task 3: A "fabricator" - which generates word lists straight from the dictionary by looking for words and their meanings.

### List Creation

Take a look at these files first:

`list_loader.py`

(Mostly standard OM code. The list creation and load parts start at around Line 208)

Here's the idea for this works:
It reads a CSV file which has all the data pertaining to the OM_LIst being created.
Header, the type of list and the word/meaning etc. (One per line)

First, get this work. 


In the interest of scaling up the List Creation, I would create a whole bunch of OM list information as CSV's, store in the director `ListsToBeCreated` and then I would create them en masse.

For this, I used the files below.

* `om_create_lists_from_directory.py`
* `om_create_lists_from_textfile.py`


