# persons 0.1a
A tool for graph-based author disambiguation. Identify distinct persons by matching forenames and surnames. Supports known persons, year data, and others. See 'examples.py' for a quick-start tutorial.

## Installation

`$ pip install persons`

## Overview

There is a wide range of people-related data. Examples include authors of publications, inventors of patents, and members of social networks. These datasets often include the names of people, but do not indicate if these names correspond to distinct persons (see next subsection on how this can become an issue). This package heuristically identifies persons from forenames and surnames and assigns person IDs. 

### Challenges of Author Disambiguation

While in many cases, names directly map to identities, there are at least two major challenges: 

* Challenge 1 (multiple variants of forename):
	* A single person can appear under several different names. This issue is often related to persons with multiple forenames. The 'persons' package deals with it by algorithmically recognizing and mapping related names.
* Challenge 2 (sharing of same name):
	* Multiple persons can share the same name. This issue is very difficult to detect without manual research and intervention in suspicious cases. Therefore, the 'persons' package provides the option to load a table of persons who were manually identified to be distinct persons ("known_persons"). 

### Approach of 'persons'

The default disambiguation procedure of 'persons' employs a graph-based, hierarchical approach:

* Step 1: 
Identify sets of name entries with identical surnames. 

* Step 2: 
Within the set of a given surname, construct a graph of the relationships of the corresponding forenames to each other. Categorize forenames as either identical, different, subsets of each other, or partially compatible ("interlaced"). For example, the forename ‘‘Michael’’ is identical to ‘‘Michael’’ and it is different from ‘‘Tom’’. In the terminology of 'persons', ‘‘Michael J.’’ is a subset of ‘‘Michael’’. This is, because ‘‘Michael J.’’ provides more specific information than ‘‘Michael’’, making it incompatible with certain names that ‘‘Michael’’ would still be compatible with. If none of those three categories applies, a record is defined as "interlaced". For example, 'persons' categorizes ‘‘M. John’’ to be interlaced with ‘‘Michael J.’’

* Step 3:
After determining all binary relationships between the names given, model the sets of forenames as nodes and their relationships as edges in a graph.

* Step 4:
Finally, eliminate "shortcuts" between nodes to determine the minimum graph and traverse the non-forking paths of subset relationships from the graph’s leafs upwards. In the example, 'persons' matches two entries with identical last names and the forenames ‘‘Michael John’’ and ‘‘Michael’’, respectively, to the same person if they are the only two forenames. It would not match them, however, if there were a ‘‘Michael Jason’’ in addition to ‘‘Michael John’’ and ‘‘Michael’’, since there would be a fork in the tree below ‘‘Michael’’.

The implementation of graph-based author disambiguation in this package has originally been created for and described in the scientific study by Önder and Schweitzer (2017).

## Using 'persons'

A quick introduction to the usage of 'persons' is provided in the 'examples.py' script that ships with this package. A brief working example employing 'pandas' is:

```
import persons

nm = persons.Persons()

import pandas as pd
name_table = pd.DataFrame({
				"fnm" 		: ["Tim", "Tim W.", "Tim J.V.", "Tim Walter"]
				,"snm" 		: ["Burton", "Burton", "Burton", "Burton"]
				,"year" 	: [1982, 1996, 2007, 2012]
			})

result = nm.persons_from_names( name_table )

print(result)
```

This returns the following result:
```
>    person_id         source  name_id         fnm     snm  matching  \
> 0          0  default table        0         Tim  Burton     equal   
> 1          1  default table        1      Tim W.  Burton  vertical   
> 2          1  default table        3  Tim Walter  Burton  vertical   
> 3          2  default table        2    Tim J.V.  Burton     equal   

>                      saving_time  year  
> 0  2017-09-17 16:43:12 CEST+0200  1982  
> 1  2017-09-17 16:43:12 CEST+0200  1996  
> 2  2017-09-17 16:43:12 CEST+0200  2012  
> 3  2017-09-17 16:43:12 CEST+0200  2007  
```

As the example demonstrates, after processing a table of names (and potentially additional information), 'persons' returns the table enhanced by a column titled 'person_id'. For each person that has been identified, 'person_id' indicates a unique number that is shared by all instances of the person. In the example given, three persons have been identified from the four names. "Tim W." and "Tim Walter" have been identified as variants of the same name and assigned the ID '1'. "Tim J.V." is not compatible with "Tim Walter" and has been assigned a different ID ('2'). "Tim" would be compatible with both of the two persons identified previously. However, since those persons are incompatible, "Tim" is assigned a separate ID ('0').

Please note that this package has been tested only for few specific use cases. The code has been optimized neither for speed, nor beauty. Bugs are to be expected. Feedback on those is welcome (sascha.schweitzer@gmail.com). 

## Matching Options

This package supports a number of alternative options for identifying persons. The options can be set by modifying the corresponding properties of a 'persons' instance. Presently, the following options are supported (default settings indicated in brackets):

### Transformations of the Input

* remove_particles_suffixes (True) 			
	* Remove particles "van", "von", "de", "d", "di", "dei", "of", "zu", "zur", "dos", "af", "der", and "graf."
* normalize_names (True) 						
	* Replace special characters (e.g., "é" by "e").

### Relation of Forenname Elements

* only_first_fnm (False) 						
	* Process only the first forename if multiple forenames are given.
* middle_name_rule (False) 					
	* Only match names if middle initial identical (cf. Jones, 2009).
* match_subsets (True) 						
	* Names with less information that are consistent are matched.
* match_interlaced (False)					
	* Names that are not identical, but have same amount/quantity of information are matched.
* ignore_order_of_forenames (False)			
	* Ignore order of forenames / middle names.

### Details if 'match_subsets' or 'match_interlaced' Set to True

* absolute_position_matters (True) 			
	* The initials, as far as they exist, of the matching names should have the same positions. Usually, the name in the first position is spelled out completely.
	* Example:

		* David 				& J. David 			are not allowed, because the first initials are different.

		* Alber Louis J.    	& Alber James 		are not allowed, because the second initials are different.

## References

* Jones, B. F. (2009). The Burden of Knowledge and the “Death of the Renaissance Man”: Is Innovation Getting Harder? Review of Economic Studies, 76(1), 283–317. http://doi.org/10.1111/j.1467-937X.2008.00531.x
* Önder, A. S., & Schweitzer, S. (2017). Catching Up or Falling Behind ? Promising Changes and Persistent Patterns across Cohorts of Economics PhDs in German-Speaking Countries from 1991 to 2008. Scientometrics, 110, 1297–1331. http://doi.org/10.1007/s11192-016-2222-9
