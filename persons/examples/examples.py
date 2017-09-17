# Copyright 2017 Sascha Schweitzer

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import persons

###
# Create an instance of 'Persons'
nm = persons.Persons()

###
# Example 1a: pandas format with year column
print( "Example 1a:")
import pandas as pd
name_table 	=	pd.DataFrame({
								"fnm" 			: 	["Tim", "Tim W."]
								,"snm" 			: 	["Burton", "Burton"]
								,"year" 		: 	[1982, 1996]
				})

result = nm.persons_from_names( name_table )

# If the input table is of type pandas, the output will be returned as
# a pandas DataFrame as well The crucial part of the result is in the
# column 'person_id'. Each unique person identified by the algorithm
# shares a person ID that is different from any other unique person.
print(result)

###
# Example 1b: pandas format with additional table of previously known persons
print( "Example 1b:")
import pandas as pd
name_table 	=	pd.DataFrame({
								"fnm" 			: 	["Tim", "Tim W."]
								,"snm" 			: 	["Burton", "Burton"]
								,"year" 		: 	[1982, 1996]
				})

known_persons= 	pd.DataFrame({
								"fnm" 			: 	["Tim", "Tim W."]
								,"snm" 			: 	["Burton", "Burton"]
				})

result = nm.persons_from_names( name_table, known_persons=known_persons, status_messages=False )

# If the input table is of type pandas, the output will be returned as a pandas DataFrame as well
print(result)

###
# Example 2a: records format with ID column
print( "Example 2a:")
name_table 	= 	[
					{ "name id" : 1, "first name" : "Albert", "last name" : "Einstein"},
					{ "name id" : 2, "first name" : "Albert L.", "last name" : "Einstein"},
					{ "name id" : 3, "first name" : "Albert Lawrence", "last name" : "Einstein"}
				]
# In this example, all names are matched to one person (under the default settings)
result = nm.persons_from_names( name_table )

# If the input table is of type records, the output will be returned as records as well
print(result)

###
# Example 2b: OrderedDict records format with ID column
print( "Example 2b:")
import collections
name_table 	= 	[
					collections.OrderedDict( [("name id" , 1) , ("first name" , "Albert"), ("last name" , "Einstein")] ),
					collections.OrderedDict( [("name id" , 2) , ("first name" , "Albert L."), ("last name" , "Einstein")] ),
					collections.OrderedDict( [("name id" , 2) , ("first name" , "Albert Lawrence"), ("last name" , "Einstein")] ),
					collections.OrderedDict( [("name id" , 3) , ("first name" , "Albert Lucky"), ("last name" , "Einstein")] )
				]
# In this example, all names are matched to different persons (under
# the default settings). Notice the difference to the previous
# example. Due to the ambiguity introduced by "Albert Lucky", the
# names cannot be consistently matched anymore.
result = nm.persons_from_names( name_table )

# If the input table is using OrderedDicts, the output will be returned using OrderedDicts as well
print(result)

###
# Example 3a: csv file with IDs and year of entry
print( "Example 3a:")
result = nm.persons_from_names( "sample_data/example_3.csv" , output_file="sample_data/persons_ex_3a.csv") 

# In addition to the output file, the function returns an OrderedDict with the results
print(result)

###
# Example 3b: csv file with IDs and year of entry and match_interlaced=True
print( "Example 3b:")
# Allowing relationships between names that are not transitive subsets
nm.match_interlaced = True
# The various "Seltens" are only matched after setting this parameter
result = nm.persons_from_names( "sample_data/example_3.csv" , output_file="sample_data/persons_ex_3b.csv") 

# In addition to the output file, the function returns an OrderedDict with the results
print(result)

###
# Example 4: xlsx file with IDs and year of entry (xlsx input requires the 'pandas' package)
print( "Example 4:")
result = nm.persons_from_names( "sample_data/example_4.xlsx") 

# The function returns an OrderedDict with the results
print(result)

