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

# General packages (packages for pandas data formats and graph plotting will be loaded later if required)
import time
import collections
from datetime import datetime
import re
import sys
import csv
import copy

import pytz

# Helper packages included in this package
from persons.support_functions.string_tools import * # functions: normalize(string), remove_particles(string)
from persons.support_functions.graph_functions import * # class: Graph, init with Graph(matrix), functions: transitive_reduction(self) - works only for transitive closure, get_single_strands(self)

class Persons(object):
	def __init__(self):
		#############################################################
		### Parameters #################################

		#####################################
		# Public

		# Transformations of the input
		self.remove_particles_suffixes 							= True
		self.normalize_names 									= True

		# Relation of the first name elements
		self.only_first_fnm 									= False
		self.middle_name_rule 									= False 	# Only match names if middle initial identical (cf. Jones, 2009)
		self.match_subsets 										= True 		# Names with less information that are consistent are matched
		self.match_interlaced									= False		# Names that are not identical, but have same amount/quantity of information are matched
		self.ignore_order_of_forenames 							= False		# Ignore order of first names / middle names

		# sub-parameter for subsets/interlaced matching (the initials, as long as they exist, of the matching names should have the same positions. Because USUALLY the frontest names are written out)
			# David 			& J. David 			are not allowed, because the first initials are different.
			# Alber Louis J.    & Alber James 		are not allowed, because the second initials are different.
		self.absolute_position_matters 							= True

		#####################################
		# Private
		# Relation of the last name elements (experimental, do not use yet)
		self._detect_marriages 									= False
		self._accept_devorce									= True

		# remove empty clusters
		self._empty_clusters_remove								= True

		# Further criteria that may distinguish persons (experimental, do not use yet)
		self._split_by_time_gap 								= False
		self._maximum_time_gap 									= 50

		# Technical parameters
		self._max_graph_size 									= 50

		self._table_with_unique_names = "known persons table"

		# Coding of the adjacency matrix (no parameter, do not change)
		self._it_subset 				= 1
		self._me_subset 				= -1

		# Timezone and time format, used in the saved data
		self._tz 						= pytz.timezone('Europe/Berlin')
		self._fmt 						= '%Y-%m-%d %H:%M:%S %Z%z'

		# two family names with a dash or with a space in between
		self._marriage_name_pattern 							= re.compile(r"^[a-z]{2,}[\s][a-z]{2,}$")

	##########################################################
	### Internal functions ################################

	def _debug_condition(snm, fnm):

		''' Returns if a value should be printed for debugging
		'''

		global debug, snm_debug, fnm_debug
		return debug and snm==snm_debug and fnm.find("M")>-1

	def _make_flat_tree(self, input_data, names, source):
		''' Make a dictionarytree with the levels . -> [last name] -> [initial first first name] -> ["records"] / ["matrix"] .
			The matrix contains a list of vectors. Each vector compares the corresponding entry of ["records"] to the other records.
		'''

		# Mapping for converting the perspective of the name comparison
		flip 							= {		self._it_subset : self._me_subset,
												self._me_subset : self._it_subset,
												"crossed" 	: "crossed",
												"different" : "different"
											}

		# Iterate over records from the database
		for row in input_data:

			#############################################################
			# Prepare data

			# only if it's not newly added virtual record	
			if "virtual_row_nr" not in row:
				# Add tag for the record source
				row["source"] 							= source["source_type"]

				# Change name of the year column to 'year'
				if source["columns"]["year_column"] is not None and row[source["columns"]["year_column"]]!="":
					row["year"] 							= int( row.pop(source["columns"]["year_column"]) )
				# Change name of the first name column to 'fnm'
				row["fnm"] 								= row.pop(source["columns"]["fnm_column"])
				# Change name of the last name column to 'snm'
				row["snm"] 								= row.pop(source["columns"]["snm_column"])
				# Change name of the ID column to 'id'
				row["id"] 								= row.pop(source["columns"]["id_column"])

				if source["name_format"]=="fnm, middle and snm":
					if "str" in str(type(row[source["columns"]["mnm_column"]])):
						# Change name of the middle name column to 'mnm'
						row["mnm"] 							= row.pop(source["columns"]["mnm_column"])
						# Strip of blanks at end and beginning
						row["mnm"] 							= row["mnm"].strip()
						# Combine first and middle name
						row["fnm"] 							+= " " + row["mnm"]
					else:
						row["mnm"] = ""

				# Normalize first name
				if row["fnm"] is not None:
					if self.only_first_fnm:
						row["fnm_normalized"] 					= normalize(row["fnm"]).split(" ")[0]
					else:
						row["fnm_normalized"] 					= normalize(row["fnm"])
				else:
					continue
				# Normalize last name
				if row["snm"] is not None:
					row["snm_normalized"] 					= normalize(row["snm"])
				else:
					continue

			# Process entry only if it's not empty
			if not(		
						row["fnm"]=="" or\
						row["snm"]=="" 
					):
						#int(row["id"]) in [20509,8105,20507,4505,7402,31386]):  
				if self.remove_particles_suffixes:
					row["snm_normalized"] 									= remove_particles(row["snm_normalized"])
				#create virtual records for possible born names (family names)
				if self._detect_marriages: 
					if self._marriage_name_pattern.match(row["snm_normalized"]) is not None:
						# to mark it that the row has been detected to have possible marriage name
						row["split_for_detecting_marriage"] 						= 1
						# if there are two normal family names after being split 
						if len(row["snm_normalized"].split()) 						== 2:
							#create a new false (virtual) record for every possible born name
							virtual_rows_to_be_appended 							= []
							for x in range(len(row["snm_normalized"].split())):
								copyrow = copy.deepcopy(row)
								#copy all infos of this record into the virtual record
								virtual_rows_to_be_appended.append(copyrow)
								#give the virtual row an virtual-row-ID for identification
								virtual_rows_to_be_appended[-1]["virtual_row_nr"] 	= x
								#give the virtual record the possible born family name as it's family name
								virtual_rows_to_be_appended[-1]["snm_normalized"] 	= (row["snm_normalized"].split())[x]
								#add a column to store the family name in the original record
								virtual_rows_to_be_appended[-1]["original_snm"] 	= row["snm_normalized"]
								#delete "split_for_detecting_marriage" because this record is not original
								del virtual_rows_to_be_appended[-1]["split_for_detecting_marriage"]
							#add the virtual records into the input data						
							for virtual_record in virtual_rows_to_be_appended:
								input_data.append(virtual_record)

				############################################################
				# Build tree

				# -1 indicates that the record doesn't belong to a cluster yet
				row["cluster"]=-1				
				
				#Level of the last name
				if row["snm_normalized"] not in names.keys():
					names[row["snm_normalized"]]				= {}							# New last name
					# The matrix indices are node indices -> each node contains all equally names records (two-sided mapping given by records_by_node and node_by_record)
					names[row["snm_normalized"]] 				= {"records": [row], "matrix": [["identical"]], "records_by_node": [[0]], "node_by_record": [0]}
				
				# If existing first letter, add record to structure and matrix
				else:
					# Assume we are dealing with a new node
					new_node 									= True
					# Create easy reference to the node name / record name mapping
					records_by_node								= names[row["snm_normalized"]]["records_by_node"]
					node_by_record								= names[row["snm_normalized"]]["node_by_record"]
					# Record number (= length of the existing list)
					record_number 								= len(names[row["snm_normalized"]]["records"])
					# Add the new record to the tree
					names[row["snm_normalized"]]["records"]		. append(row)
					# Start new node (will be removed again, if record turns out to be equal to existing node)
					records_by_node 							. append([record_number])
					# Start new row in matrix (will be removed again, if record turns out to be equal to existing node)
					names[row["snm_normalized"]]["matrix"] 		. append([])
					########################################################
					## Comparison of all record-existing node combinations (comparison matrix ["matrix"])
					# Iterate over all existing nodes
					for existing_node_index in range( len( names[row["snm_normalized"]]["matrix"] )-1 ):
						# Compare new record to an existing record (from the perspecitve of the new entry)
						comparison_result=self._compare(row["fnm_normalized"], names[row["snm_normalized"]]["records"][ records_by_node[existing_node_index][0] ]["fnm_normalized"])
						#print("comparing:", row["fnm_normalized"], names[row["snm_normalized"]]["records"][ records_by_node[existing_node_index][0] ]["fnm_normalized"],comparison_result)
						# If row is equal to existing
						if comparison_result=="equal":
							# Whoa, wait, this is not a new node
							new_node 							= False
							# Map to an existing node
							records_by_node[existing_node_index].append(record_number)
							#original: node_by_record.append(node_by_record[existing_node_index])
							node_by_record.append(existing_node_index)
							# Remove the matrix row added for the wrongly assumed new node
							names[row["snm_normalized"]]["matrix"].pop(-1)
							# Remove the new node added for the wrongly assumed new node
							records_by_node 					. pop(-1) # WL: the record number of the one, whose forename has never appeared 
							# This is all an Alter Hut, let's not waste our time here with more comparisons
							#print("equal",row,names[row["snm_normalized"]]["records"][records_by_node[existing_node_index][0] ])
							break
						else:
							# Append to the new record's matrix vector (horizontal part of the matrix)
							names[row["snm_normalized"]]["matrix"][-1].append(comparison_result)

					if new_node:
						# Map current record to a new node
						node_by_record 							. append( len(records_by_node)-1 )
						# Add comparison to the new node itself (it's not only equal, but identical to itself)
						names[row["snm_normalized"]]["matrix"][-1].append("identical")
						# Fill the vertical parts of the existing nodes vectors with the additional entry (kind of a waste, but we like squares - go Spongebob, go!)
						for existing_node_index in range( len( names[row["snm_normalized"]]["matrix"] )-1 ):
							names[row["snm_normalized"]]["matrix"][existing_node_index].append( flip[ names[row["snm_normalized"]]["matrix"][-1][existing_node_index] ] )

		# remove snm_key, which only contains virtual records
		if self._detect_marriages:					
			for snm_key in sorted(names):
				try:
					if all (names[snm_key]["records"][y]["virtual_row_nr"] >= 0 for y in range(len(names[snm_key]["records"]))):
						names.pop(snm_key)
				except:
					pass

	def _find_interrelated(self, names, snm_key, to_process, relevant_relations, matching_code=set()): # WL: set(): disordered without repetition
		''' Find all nodes that are interrelated (to the first node to be processed and each other)
		'''

		interrelated 			= set( [to_process[0]] )
		interrelated_new 		= set( [to_process[0]] )
		to_process 				. remove(to_process[0])
		while len(interrelated_new)>0:

			temp			 	= set()
			# Iterate over all new items
			for i_node in interrelated_new:
				# Iterate over all not assigned items
				for i_other_node in to_process:
					# Check if the item to be compared matches an item of the interrelated cluster
					if i_other_node not in temp and names[snm_key]["matrix"][i_node][i_other_node] in relevant_relations:
						temp.add(i_other_node)
						if names[snm_key]["matrix"][i_node][i_other_node]=="crossed":
							matching_code.add("interlaced")
						elif names[snm_key]["matrix"][i_node][i_other_node] in [self._me_subset, self._it_subset]:
							matching_code.add("vertical")
			# Remove items assigned to the interrelated cluster from the list of items to be processed
			for item in temp:
				to_process.remove(item)
			# Store items assigned as the new related items
			interrelated_new 	= temp
			interrelated 		. update(interrelated_new)
		return interrelated

	def _cluster(self, names, cluster_list, cluster_number_list):
		''' Cluster records from the given tree
		'''

		######################################################
		# Identify related names. Sort into same cluster if compatible. Mark as ambiguous if incompatible.
		# Level of the last name
		for snm_key in sorted(names):
			# Nodes to be processed
			to_be_processed 			= list( range( len(names[snm_key]["records_by_node"]) ) )

			# Create easy reference to the node name / record name mapping
			records_by_node								= names[snm_key]["records_by_node"]
			node_by_record								= names[snm_key]["node_by_record"]

			while len(to_be_processed)>0:
				# None of the interrelated items is "different" / mutually exclusive from the other (per interrelated group)
				interrelated_consistent 					= True

				# Initialize tag reporting which relationships occured in the matching
				matching_code 								= set(["equal"])

				#####################################################################
				# Match all related items (match_subsets_and_interlaced==True)
				if self.match_interlaced and self.match_subsets and interrelated_consistent:
				# original: if match_subsets_and_interlaced and interrelated_consistent:
					# Break condition for the case a pure subset is removed (move back to while loop in that case)
					pure_subset_removed 					= False
					# Reset the matching code
					matching_code 							= set(["equal"])
					# Find all nodes that are interrelated (to the first node to be processed and each other)
					interrelated 							= self._find_interrelated(names, snm_key, to_be_processed, ["identical", self._me_subset, self._it_subset, "crossed"], matching_code)

					#########################################
					# Check consistency of the set of interrelated items

					# Find pure subsets with conflicting supersets
					for item in interrelated:
						# Only for pure subsets
						if self._it_subset not in names[snm_key]["matrix"][item] and "crossed" not in names[snm_key]["matrix"][item] and not pure_subset_removed:
							# Compare all their supersets
							for first in interrelated:
								if names[snm_key]["matrix"][item][first]==self._me_subset and not pure_subset_removed:
									for second in interrelated:
										if names[snm_key]["matrix"][item][second]==self._me_subset and not pure_subset_removed:
											# If the supersets of the pure subset are conflicting
											if names[snm_key]["matrix"][first][second]=="different":
												pure_subset_removed 	= True
												item_to_remove 			= item
											# _find_interrelated might not have checked all possible pairs for "crossed" relationships, therefore add this info to matching_code
											elif names[snm_key]["matrix"][first][second]=="crossed":
												matching_code.add("interlaced")

					# Remove the pure subset
					if pure_subset_removed:
						# Assign the pure subset to a cluster
						for i_record in records_by_node[item_to_remove]:
							# Reset the matching code
							matching_code 							= set(["equal"])
							# Assign cluster to record
							names[snm_key]["records"][i_record]["cluster"]=self._cluster_number
							names[snm_key]["records"][i_record]["matching"]=matching_code
							# record the cluster nr and id for rework for marriage name later
							if self._detect_marriages:
								if "split_for_detecting_marriage" in names[snm_key]["records"][i_record]:
									if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
									cluster_number_list[names[snm_key]["records"][i_record]["id"]][0] = self._cluster_number
								elif "virtual_row_nr" in names[snm_key]["records"][i_record]:
									if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
									if names[snm_key]["records"][i_record]["virtual_row_nr"] == 0:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]][1] = self._cluster_number
									else:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]][2] = self._cluster_number
							# Check if cluster exists in list of clusters (and add if non-existent)
							if self._cluster_number not in cluster_list.keys():
								cluster_list[self._cluster_number]=[]
							# Append the record to the cluster list
							cluster_list[self._cluster_number].append(names[snm_key]["records"][i_record])
						# Continue with next cluster number
						self._cluster_number		+=1
						# Remove from the set of interrelated items
						interrelated.remove(item_to_remove)
						# Change matrix to make the item different
						for element in range( len(names[snm_key]["matrix"][item_to_remove])):
							if element!=item_to_remove:
								names[snm_key]["matrix"][item_to_remove][element]="different"
								names[snm_key]["matrix"][element][item_to_remove]="different"
						# Add the other interrelated items to the items to be processed
						to_be_processed 		= to_be_processed + list(interrelated)

					# If a pure subset has been removed, go back to the while loop
					else:
						# For all pairs
						for first in interrelated:
							for second in interrelated:
								# Check their consistency
								if names[snm_key]["matrix"][first][second]=="different":
									interrelated_consistent 	= False
									# Set of interrelated needs to be processed again (in the code for single-strand matching below)
									to_be_processed_level_2		= list( interrelated.copy() )

						# If interrelated_consistent all entries get the same id
						if interrelated_consistent:
							# Assign a new cluster number
							for i_node in interrelated:
								# Iterate over all records in the node (equal names)
								for i_record in records_by_node[i_node]:
									# Assign cluster to record
									names[snm_key]["records"][i_record]["cluster"]=self._cluster_number
									names[snm_key]["records"][i_record]["matching"]=matching_code
									# record the cluster nr and id for rework for marriage name later
									if self._detect_marriages:
										if "split_for_detecting_marriage" in names[snm_key]["records"][i_record]:
											if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
												cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
											cluster_number_list[names[snm_key]["records"][i_record]["id"]][0] = self._cluster_number
										elif "virtual_row_nr" in names[snm_key]["records"][i_record]:
											if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
												cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
											if names[snm_key]["records"][i_record]["virtual_row_nr"] == 0:
												cluster_number_list[names[snm_key]["records"][i_record]["id"]][1] = self._cluster_number
											else:
												cluster_number_list[names[snm_key]["records"][i_record]["id"]][2] = self._cluster_number
									# Check if cluster exists in list of clusters (and add if non-existent)
									if self._cluster_number not in cluster_list.keys():
										cluster_list[self._cluster_number]=[]
									# Append the record to the cluster list
									cluster_list[self._cluster_number].append(names[snm_key]["records"][i_record])
							
							# Continue with next cluster number
							self._cluster_number+=1

				#####################################################################
				# Match subsets (match_subsets_and_interlaced==False and match_subsets=True)
				if self.match_subsets and ( self.match_interlaced==False or not(interrelated_consistent) ):

					# Process only interrelated items from the previous interlaced part (if with interlaced) or process all items
					if not(self.match_interlaced):
						to_be_processed_level_2 				= to_be_processed

					while len(to_be_processed_level_2)>0:

						# Break condition for the case a pure subset is removed (move back to while loop in that case)
						pure_subset_removed 					= False

						# Find all nodes that are interrelated (to the first node to be processed and each other)
						interrelated 							= self._find_interrelated(names, snm_key, to_be_processed_level_2, ["identical", self._me_subset, self._it_subset], set() )

						# Find pure subsets with conflicting supersets
						for item in interrelated:
							# Only for pure subsets
							if self._it_subset not in names[snm_key]["matrix"][item] and "crossed" not in names[snm_key]["matrix"][item] and not pure_subset_removed:
								# Compare all their supersets
								for first in interrelated:
									if names[snm_key]["matrix"][item][first]==self._me_subset and not pure_subset_removed:
										for second in interrelated:
											if names[snm_key]["matrix"][item][second]==self._me_subset and not pure_subset_removed:
												# If the supersets of the pure subset are conflicting
												if names[snm_key]["matrix"][first][second]=="different":
													pure_subset_removed 	= True
													item_to_remove 			= item

						# Remove the pure subset
						if pure_subset_removed:
							# Assign the pure subset to a cluster
							for i_record in records_by_node[item_to_remove]:
								# Assign cluster to record
								names[snm_key]["records"][i_record]["cluster"]=self._cluster_number
								names[snm_key]["records"][i_record]["matching"]=matching_code
								# record the cluster nr and id for rework for marriage name later
								if self._detect_marriages:
									if "split_for_detecting_marriage" in names[snm_key]["records"][i_record]:
										if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
											cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
										cluster_number_list[names[snm_key]["records"][i_record]["id"]][0] = self._cluster_number
									elif "virtual_row_nr" in names[snm_key]["records"][i_record]:
										if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
											cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
										if names[snm_key]["records"][i_record]["virtual_row_nr"] == 0:
											cluster_number_list[names[snm_key]["records"][i_record]["id"]][1] = self._cluster_number
										else:
											cluster_number_list[names[snm_key]["records"][i_record]["id"]][2] = self._cluster_number
								# Check if cluster exists in list of clusters (and add if non-existent)
								if self._cluster_number not in cluster_list.keys():
									cluster_list[self._cluster_number]=[]
								# Append the record to the cluster list
								cluster_list[self._cluster_number].append(names[snm_key]["records"][i_record])
							# Continue with next cluster number
							self._cluster_number		+=1
							# Remove from the set of interrelated items
							interrelated.remove(item_to_remove)
							# Change matrix to make the item different
							for element in range( len(names[snm_key]["matrix"][item_to_remove])):
								if element!=item_to_remove:
									names[snm_key]["matrix"][item_to_remove][element]="different"
									names[snm_key]["matrix"][element][item_to_remove]="different"
							# Add the other interrelated items to the items to be processed
							to_be_processed_level_2		= to_be_processed_level_2 + list(interrelated)
						# If a pure subset has been removed, go back to the while loop
						else:

							########################################
							# Search for chains of subsets (without forks)

							if len(interrelated)>1 and len(interrelated)<=self._max_graph_size:
								# Graph (create from adjacency matrix)
								G 										= Graph(names[snm_key]["matrix"], list(interrelated))

								# Transitive reduction
								G 										. transitive_reduction()

								# Single stranded parts of the graph
								single_strands 							= G.get_single_strands()
							# To big graphs are bad
							elif len(interrelated)>self._max_graph_size:
								single_strands 							= [ [x] for x in interrelated]
							# If there is only one node, no graph needed (case is redundant with the previous one)
							else:
								single_strands 							= [list(interrelated)]

							#######################################
							# Assign cluster numbers to the cleaned clusters
							for strand in single_strands:
								# If only one element, no vertical relationship
								if len(strand)==1:
									matching_code 						= set(["equal"])
								else:
									matching_code 						= set(["vertical"])
								# Assign a new cluster number
								for i_node in strand:
									# Iterate over all records in the node (equal names)
									for i_record in records_by_node[i_node]:
										# Assign cluster to record
										names[snm_key]["records"][i_record]["cluster"]=self._cluster_number
										names[snm_key]["records"][i_record]["matching"]=matching_code
										# record the cluster nr and id for rework for marriage name later
										if self._detect_marriages:
											if "split_for_detecting_marriage" in names[snm_key]["records"][i_record]:
												if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
													cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
												cluster_number_list[names[snm_key]["records"][i_record]["id"]][0] = self._cluster_number
											elif "virtual_row_nr" in names[snm_key]["records"][i_record]:
												if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
													cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
												if names[snm_key]["records"][i_record]["virtual_row_nr"] == 0:
													cluster_number_list[names[snm_key]["records"][i_record]["id"]][1] = self._cluster_number
												else:
													cluster_number_list[names[snm_key]["records"][i_record]["id"]][2] = self._cluster_number
										# Check if cluster exists in list of clusters (and add if non-existent)
										if self._cluster_number not in cluster_list.keys():
											cluster_list[self._cluster_number]=[]
										# Append the record to the cluster list
										cluster_list[self._cluster_number].append(names[snm_key]["records"][i_record])
								# Continue with next cluster number
								self._cluster_number+=1

					# If only subsets are matched, sync back items to be processed
					if not(self.match_interlaced):
						 to_be_processed				= to_be_processed_level_2

				# If neither interlaced nor subsets shall be matched, match only the equal/identical entries
				if not(self.match_subsets):
					# Process all items until none is left
					for i_node in to_be_processed:
						for i_record in records_by_node[i_node]:
							names[snm_key]["records"][i_record]["cluster"]=self._cluster_number
							names[snm_key]["records"][i_record]["matching"]=matching_code
							# record the cluster nr and id for rework for marriage name later
							if self._detect_marriages:
								if "split_for_detecting_marriage" in names[snm_key]["records"][i_record]:
									if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
									cluster_number_list[names[snm_key]["records"][i_record]["id"]][0] = self._cluster_number
								elif "virtual_row_nr" in names[snm_key]["records"][i_record]:
									if names[snm_key]["records"][i_record]["id"] not in cluster_number_list:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]] = {}
									if names[snm_key]["records"][i_record]["virtual_row_nr"] == 0:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]][1] = self._cluster_number
									else:
										cluster_number_list[names[snm_key]["records"][i_record]["id"]][2] = self._cluster_number
							# Check if cluster exists in list of clusters (and add if non-existent)
							if self._cluster_number not in cluster_list.keys():
								cluster_list[self._cluster_number]=[]
							# Append the record to the cluster list
							cluster_list[self._cluster_number].append(names[snm_key]["records"][i_record])
						# Continue with next cluster number
						self._cluster_number+=1
					# End the while loop
					break

		######################################################
		## Split or invalidate clusters with multiple distinct persons
		copy_keys_cluster_list=list(cluster_list.keys())		# copy to avoid changing of iterator during iteration, deep is not required
		for i_cluster in copy_keys_cluster_list:

			# Collect unique entries
			known_unique 						= [record for record in cluster_list[i_cluster] if record["source"]==self._table_with_unique_names]

			# If multiple phds in the cluster
			if len(known_unique)>1:

				# Create new clusters for unique entries
				indices_new_clusters 			= []
				for record in known_unique:
					record["matching"]=set(["multiple known persons separated"])
					record["cluster"] 				= self._cluster_number
					cluster_list[self._cluster_number]= [record]
					indices_new_clusters.append(self._cluster_number)
					# Increase cluster number
					self._cluster_number 				+=1 
					# Remove known unique from previous cluster
					cluster_list[i_cluster].remove(record)
				# Move those records to the new clusters that are equal
				for index_new_cluster in indices_new_clusters:
					unique_fnm = cluster_list[index_new_cluster][0]["fnm_normalized"]
					for record in cluster_list[i_cluster]:
						non_unique_fnm = record["fnm_normalized"]
						# Check for equality
						if self._compare(unique_fnm, non_unique_fnm)=="equal":
							record["matching"]=set(["multiple known persons separated"])
							record["cluster"] 			= index_new_cluster
							cluster_list[index_new_cluster].append(record)
							cluster_list[i_cluster].remove(record)
						else:
							record["matching"]=set(["moved from multiple known persons"])

		######################################################
		## Marriage detection
		if self._detect_marriages:					
			# clean up the clusters, which contain only virtual records
			for cluster in sorted(cluster_list):
				try:
					if all (cluster_list[cluster][y]["virtual_row_nr"] >= 0 for y in range(len(cluster_list[cluster]))):
						for record in cluster_list[cluster]:
							#print(cluster_number_list[record["id"]])
							del cluster_number_list[record["id"]][record["virtual_row_nr"]+1]
							#print("after deleting", cluster_number_list[record["id"]])
						del cluster_list[cluster][:]
				except:
					pass
			# find out the original records, whose virtual records were both cleaned up
			for cluster in sorted(cluster_number_list):
				if len(cluster_number_list[cluster]) < 2:
					for record in range(len(cluster_list[cluster_number_list[cluster][0]])):
						cluster_list[cluster_number_list[cluster][0]][record]["split_for_detecting_marriage"] = "possible born surname not found"
					del cluster_number_list[cluster]

	def _compare(self, me, it):
		''' Comparison of first names from the perspective of the first parameter
		'''

		if me==it:
			return "equal"
		elif not( self.middle_name_rule or self.match_subsets or self.match_interlaced ):
			return "different"

		me=me.split(" ")
		it=it.split(" ")

		# If me and it do neither share a full name nor an initial, they are different
		# Simple version (equality has been tested above)
		if len(me)==1 and len(it)==1 and me[0][0:1]!=it[0][0:1]:
			return "different"
		# General version of completely different 
		if len( set(me + [x[0:1] for x in me]).intersection(set(it +[x[0:1] for x in it])) )==0:
			return "different"
		# Common case that first firstname equal and second missing or initial
		if len(me)<3 and len(it)<3 and me[0]==it[0] and not self.middle_name_rule:
			# If one has only one first name, it's a subset
			if len(me)==1:
				return self._me_subset
			elif len(it)==1:
				return self._it_subset
			# If one name has an initial as second first name that matches the other second first name, it's a subset
			elif len(me[1])==1 and me[1]==it[1][0:1]:
				return self._me_subset
			elif len(it[1])==1 and it[1]==me[1][0:1]:
				return self._it_subset

		# If first name is equal and all middle names have the same initial (Jone's rule)
		if self.middle_name_rule:
			if len(me)>1 and len(it)>1 and len(me)==len(it):
				# If first names are equal
				if me[0]==it[0]:
					# Iterate over all middle names
					for index in range( 1,len(me) ):
						# If one of the initials differ, names are different
						if me[index][0:1]!=it[index][0:1]:
							return "different"
				# If first names are different
				else:
					return "different"
			# If not the same number of first names
			else:
				return "different"
			# If none of the middle name initials is different
			return "equal"
		# If first names can be in different order and subsets play a role
		elif self.ignore_order_of_forenames:
			# Check how me_parts relate to the other
			part_comparison_me 								= []
			for index_first in range(len(me)):
				first 										= me[index_first]
				part_comparison_me 							.append("unknown")
				copy_it 									= it[:]
				# Check if first of me is somewhere in 'it'
				index_second								= 0
				while index_second < len(copy_it):
					second 									= copy_it[index_second]
					if first==second:
						part_comparison_me[index_first] 	= "equal"
						copy_it.pop(index_second)
						break
					elif first==second[0:1]:
						part_comparison_me[index_first] 	= "me_initial"
						copy_it.pop(index_second)
						break
					elif first[0:1]==second:
						part_comparison_me[index_first] 	= "it_initial"
						copy_it.pop(index_second)
						break
					index_second 							+=1

			# Check how it_parts relate to me
			part_comparison_it 								= []
			for index_first in range(len(it)):
				first 										= it[index_first]
				part_comparison_it 							.append("unknown")
				copy_me 									= me[:]
				# Check if first of it is somewhere in 'me'
				index_second								= 0
				while index_second < len(copy_me):
					second 									= copy_me[index_second]
					if first==second:
						part_comparison_it[index_first] 	= "equal"
						copy_me.pop(index_second)
						break
					elif first==second[0:1]:
						part_comparison_it[index_first] 	= "it_initial"
						copy_me.pop(index_second)
						break
					elif first[0:1]==second:
						part_comparison_it[index_first] 	= "me_initial"
						copy_me.pop(index_second)
						break
					index_second 							+=1

			# Convert to set (for using set functions)
			part_comparison_me 								= set(part_comparison_me)
			part_comparison_it 								= set(part_comparison_it)
			part_comparison_all								= part_comparison_it.union(part_comparison_me)

			# it shorter (I have more names) - it should be subset, unless elements are not in me (different) or I'm subset as well (crossed)
			if len(me) > len(it):
				if "unknown" in part_comparison_it:
					return "different"
				elif "me_initial" in part_comparison_all:
					return "crossed"
				else:
					return self._it_subset
			# me shorter (I have fewer names)
			elif len(me) < len(it):
				if "unknown" in part_comparison_me:
					return "different"
				elif "it_initial" in part_comparison_all:
					return "crossed"
				else:
					return self._me_subset
			else:
				if len( part_comparison_all.difference(set(["equal"])) )==0:
					return "equal"
				elif "unknown" in part_comparison_all:
					return "different"
				elif "me_initial" in part_comparison_all and "it_initial" in part_comparison_all:
					return "crossed"
				elif "me_initial" in part_comparison_all:
					return self._me_subset
				elif "it_initial" in part_comparison_all:
					return self._it_subset

		# If order of the first names needs to be respected and subsets play a role
		else:
			comparing_continue = True
			# if positions of initials should be checked
			if self.absolute_position_matters:
				for initial_position in range(min(len(me),len(it))):
					if me[initial_position][0] != it[initial_position][0]:
						return "different"
						comparing_continue = False
						break

			# if positions are the same or if position doesn't play a role
			if comparing_continue:
				index_last_found 								= 0
				part_comparison_me 								= []
				for index_first in range( len(me) ):
					first 										= me[index_first]
					part_comparison_me 							.append("unknown")
					# Check if first of me is somewhere in 'it'
					if index_last_found < len(it):
						for index_second in range( index_last_found, len(it) ):
							second 									= it[index_second]
							if first==second:
								part_comparison_me[index_first] 	= "equal"
								index_last_found 					= index_second+1
								break
							elif first==second[0:1]:
								part_comparison_me[index_first] 	= "me_initial"
								index_last_found 					= index_second+1
								break
							elif first[0:1]==second:
								part_comparison_me[index_first] 	= "it_initial"
								index_last_found 					= index_second+1
								break
				# it shorter (I have more names)
				if len(me) > len(it):
					# If it has some part that don't match me (even though it is smaller)
					if (len(part_comparison_me) - part_comparison_me.count("unknown")) < len(it):
						return "different"
					elif "me_initial" in part_comparison_me:
						return "crossed"
					else:
						return self._it_subset
				# me shorter (I have fewer names)
				elif len(me) < len(it):
					if "unknown" in part_comparison_me:
						return "different"
					elif "it_initial" in part_comparison_me:
						return "crossed"
					else:
						return self._me_subset
				else:
					if "unknown" in part_comparison_me:
						return "different"
					elif "me_initial" in part_comparison_me and "it_initial" in part_comparison_me:
						return "crossed"
					elif "me_initial" in part_comparison_me:
						return self._me_subset
					elif "it_initial" in part_comparison_me:
						return self._it_subset

	def _time_gap(self, cluster_list, maximum_time_gap, cluster_number_list, action="report"):
		''' Save cluster_list to the authors table
		'''
		# Original keys of the cluster list for the iteration
		original_keys 												= list(cluster_list.keys())

		for i_cluster in original_keys:

			# Sort records in the cluster by their year stamp
			cluster_list[i_cluster] 								= sorted(cluster_list[i_cluster], key=lambda k: k['year']) 

			if action=="split":
				# Memorize when new cluster started
				new_cluster_started 									= False
				# Collect items to be removed 
				to_be_removed  											= []

				for i_record in range( len(cluster_list[i_cluster]) ):

					# If new cluster has been started, sort all further items into it
					if new_cluster_started:
						cluster_list[i_cluster][i_record]["cluster"] 	= self._cluster_number
						# record the cluster nr and id for rework for marriage name later
						if self._detect_marriages and cluster_list[i_cluster][i_record]["id"] in cluster_number_list:
							if "split_for_detecting_marriage" in cluster_list[i_cluster][i_record]:
								cluster_number_list[cluster_list[i_cluster][i_record]["id"]][0] = self._cluster_number
							elif "virtual_row_nr" in cluster_list[i_cluster][i_record]:
								if cluster_list[i_cluster][i_record]["virtual_row_nr"] == 0:
									cluster_number_list[cluster_list[i_cluster][i_record]["id"]][1] = self._cluster_number
								else:
									cluster_number_list[cluster_list[i_cluster][i_record]["id"]][2] = self._cluster_number
						cluster_list[self._cluster_number]					. append(cluster_list[i_cluster][i_record])
						to_be_removed 									. append(cluster_list[i_cluster][i_record])

					# If time gap between two records exceeds limit
					if i_record < len(cluster_list[i_cluster])-1 and int(cluster_list[i_cluster][i_record+1]['year']) - int(cluster_list[i_cluster][i_record]['year']) > maximum_time_gap:
						# Start new cluster
						new_cluster_started 							= True
						self._cluster_number 								+=1
						# Add new cluster
						cluster_list[self._cluster_number] 				= []

				if new_cluster_started:
					for record in cluster_list[i_cluster]:
						record["matching"].add("split at time gap")
				for i_record in to_be_removed:
					cluster_list[i_cluster].remove(i_record)

			if action=="report":

				# Maximum time gap observed
				max_gap_observed 										= 0

				for i_record in range( len(cluster_list[i_cluster])-1 ):
					if int(cluster_list[i_cluster][i_record+1]['year']) - int(cluster_list[i_cluster][i_record]['year']) > max_gap_observed:
						max_gap_observed 								= int(cluster_list[i_cluster][i_record+1]['year']) - int(cluster_list[i_cluster][i_record]['year']) 

				for i_record in range( len(cluster_list[i_cluster]) ):
					cluster_list[i_cluster][i_record]['maximum_time_gap'] = max_gap_observed

		if self._detect_marriages:					
			# clean up the clusters, which contain only virtual records
			for cluster in sorted(cluster_list):
				try:
					if all (cluster_list[cluster][y]["virtual_row_nr"] >= 0 for y in range(len(cluster_list[cluster]))):
						for record in cluster_list[cluster]:
							#print(cluster_number_list[record["id"]])
							del cluster_number_list[record["id"]][record["virtual_row_nr"]+1]
							#print("after deleting", cluster_number_list[record["id"]])
						del cluster_list[cluster][:]

				except:
					pass
			# find out the original records, whose virtual records were both cleaned up
			for cluster in sorted(cluster_number_list):
				if len(cluster_number_list[cluster]) < 2:
					for record in range(len(cluster_list[cluster_number_list[cluster][0]])):
						cluster_list[cluster_number_list[cluster][0]][record]["split_for_detecting_marriage"] = "possible born surname found"
						cluster_list[cluster_number_list[cluster][0]][record]["matching"].add("split at time gap")
					del cluster_number_list[cluster]

	def _rework_for_marriages(self, cluster_list, cluster_number_list):
		# all the virtual records which now enter this function have fulfilled the criteria above. If the two virtual records for an original one are allocated into different clusters, it means the original record could be different persons, so make it ambiguous
		# the matching_codes are only combined, if matched. For an ambigous born surname, the matching_codes of the virtual record remain in other records in the same cluster, but not in its original record, because of the other ambigous born surname

		#try:
		for i_id in sorted(cluster_number_list):
			new_cluster_nr_add = False
			new_cluster_nr = []

			###########################################################################################
			# find out the conflicting situations, where two virtual records still exist 
			if len(cluster_number_list[i_id]) > 2:
				for threeclusters in range(len(cluster_number_list[i_id])):
					for record in cluster_list[cluster_number_list[i_id][threeclusters]]:
						record["split_for_detecting_marriage"] = "ambiguous born surnames found" 
						# clear this dictionary, but not deleted (because of for loop)
				cluster_number_list[i_id].clear()		
			
			############################################################################################	
			# if there is no conflicting virtual record anymore, only one virtual record still exists
			elif len(cluster_number_list[i_id]) == 2:
				#if not yet in the same cluster (because of other records, the real and the virtual record could already be brought into the same cluster)
				i_cluster = cluster_number_list[i_id][0]
				virtual_cluster = cluster_number_list[i_id][sorted(cluster_number_list[i_id])[-1]]
				if i_cluster != virtual_cluster:
					# create a comparing list for all records (only containing names and years) from the clusters, to which the original record could belong 
					comparing_list = []
					# add names, years of the records in the cluster, where the virtual record is, into the comparing list									
					length_virtual_cluster = len(cluster_list[virtual_cluster])
					for record1 in range(length_virtual_cluster):
						comparing_list.append({})
						comparing_list[-1]["year"] = cluster_list[virtual_cluster][record1]["year"]
						# original name is changed back for comparing
						if "virtual_row_nr" in cluster_list[virtual_cluster][record1]:
							comparing_list[-1]["snm_normalized"] = cluster_list[virtual_cluster][record1]["original_snm"]
						else:
							comparing_list[-1]["snm_normalized"] = cluster_list[virtual_cluster][record1]["snm_normalized"]
					# add all the records in the cluster, where the original record is, into the comparing list
					for record0 in range(len(cluster_list[i_cluster])):
						comparing_list.append({})
						comparing_list[-1]["year"] = cluster_list[i_cluster][record0]["year"]
						# if one record is a virtual record, the surname should be replaced by its original name for comparing
						if "virtual_row_nr" in cluster_list[i_cluster][record0]:
							comparing_list[-1]["snm_normalized"] = cluster_list[i_cluster][record0]["original_snm"]
						else:
							comparing_list[-1]["snm_normalized"] = cluster_list[i_cluster][record0]["snm_normalized"]
					#all records in the comparing list are ordered by year of the publication
					comparing_list = sorted(comparing_list, key=lambda k: k['year'])

					# how many times the name has been changed, is counted
					change_time = 0
					for x in range(len(comparing_list)):
						if x < len(comparing_list)-1 and comparing_list[x+1]["snm_normalized"] != comparing_list[x]["snm_normalized"]:
							change_time += 1

					''' shouldn't be happening:
					# for the situation like "Jane Smith-Miller","Jane Smith-Miller","Jane Smith-Miller", where only combinations exist and those are the same
					if change_time == 0:		
						# there are only virtual records in the cluster, where the virtual record is (maybe split by time gap)
						for record2 in range(len(cluster_list[i_cluster])):
							cluster_list[i_cluster][record2]["split_for_detecting_marriage"] = "possible born surname not found"
					'''		

					# conflicting REAL name combinations, such as "Jane Smith","Jane Smith-Miller","Jane Smith-Walker"
					conflicting_name_combination_found = False
					for first_real_name_delete in range(len(comparing_list)):
						if len(comparing_list[first_real_name_delete]["snm_normalized"].split()) > 1:
							for second_real_name_delete in range(len(comparing_list)):
								if len(comparing_list[second_real_name_delete]["snm_normalized"].split()) > 1 and comparing_list[first_real_name_delete]["snm_normalized"] != comparing_list[second_real_name_delete]["snm_normalized"]:
									conflicting_name_combination_found = True
									# mark the record in cluster, where the virtual cluster are, ambiguous
									for record8 in range(len(cluster_list[virtual_cluster])):
										cluster_list[virtual_cluster][record8]["split_for_detecting_marriage"] = "conflicting marriage name combinations"
									# mark the record in cluster, where the original cluster are, ambiguous
									for record3 in range(len(cluster_list[i_cluster])):
										cluster_list[i_cluster][record3]["split_for_detecting_marriage"] = "conflicting marriage name combinations"
										cluster_number_list[cluster_list[i_cluster][record3]["id"]].clear()

					# if there is no conflicting name combinations
					if not conflicting_name_combination_found:
						# regarding devorce:
							# Situation like Jane Smith-Miller & Jane Smith & Jane Smith-Miller
							# Situation like Jane Smith & Jane Smith-Miller & Jane Smith & Jane Smith-Miller
						# 			or no devorce: 
							# Situation like (Jane Smith-Miller & Jane Smith)
							# Situation like (Jane Smith & Jane Smith-Miller & Jane Smith)
						# are allowed

						# if unallowed situation happends, the records in the comparing list belong to different persons:
						if (accept_devorce and len(comparing_list[0]["snm_normalized"].split()) > 1 and change_time > 1) or \
							(accept_devorce and len(comparing_list[0]["snm_normalized"].split()) == 1 and change_time > 2) or \
							(not accept_devorce and len(comparing_list[0]["snm_normalized"].split()) > 1 and change_time > 0) or \
							(not accept_devorce and len(comparing_list[0]["snm_normalized"].split()) == 1 and change_time > 1) :

							for record9 in range(len(cluster_list[virtual_cluster])):
								cluster_list[virtual_cluster][record9]["split_for_detecting_marriage"] = "non-linear surname changes"
							for record4 in range(len(cluster_list[i_cluster])):
								cluster_list[i_cluster][record4]["split_for_detecting_marriage"] = "non-linear surname changes"
								if cluster_list[i_cluster][record4]["id"] in cluster_number_list and len(cluster_number_list[cluster_list[i_cluster][record4]["id"]]) > 0:
									cluster_number_list[cluster_list[i_cluster][record4]["id"]].clear()

						# if the records in the comparing list belong to the same person:
						else:
							new_cluster_nr_add = True
							new_cluster_nr.append(i_cluster)
							new_matching_code = cluster_list[virtual_cluster][0]["matching"].union(cluster_list[i_cluster][0]["matching"])

							#move the records in the cluster, where the original record is, into the cluster, where the virtual one is
							while len(cluster_list[virtual_cluster]) > 0:
								# record the cluster nr and id for rework for marriage name later
								if "split_for_detecting_marriage" in cluster_list[virtual_cluster][-1]:
									cluster_number_list[cluster_list[virtual_cluster][-1]["id"]][0] = new_cluster_nr[-1]
								elif "virtual_row_nr" in cluster_list[virtual_cluster][-1]:
									if cluster_list[virtual_cluster][-1]["virtual_row_nr"] == 0:
										cluster_number_list[cluster_list[virtual_cluster][-1]["id"]][1] = new_cluster_nr[-1]
									else:
										cluster_number_list[cluster_list[virtual_cluster][-1]["id"]][2] = new_cluster_nr[-1]
								cluster_list[i_cluster].append(cluster_list[virtual_cluster][-1])
								cluster_list[virtual_cluster].pop(-1)
							for record7 in range(len(cluster_list[i_cluster])):
								cluster_list[i_cluster][record7]["split_for_detecting_marriage"] = "matched for the possible surname change"
								cluster_list[i_cluster][record7]["matching"] = new_matching_code
								if cluster_list[i_cluster][record7]["id"] in cluster_number_list and len(cluster_number_list[cluster_list[i_cluster][record7]["id"]]) > 0:
									cluster_number_list[cluster_list[i_cluster][record7]["id"]].clear() 
							#for all_new_record_to_fix in range(len(cluster_list[virtual_cluster])):
								#cluster_list[virtual_cluster][all_new_record_to_fix]["matching"] = str(original_matching_code_part1.union(virtual_matching_code_part1)) + original_matching_code_part2 + virtual_matching_code_part2
			else:
				pass
		#except:
			#pass

		#clean up the virtual records in the cluster
		for fix_cluster in sorted(cluster_list):
			fix_record = 0
			while fix_record < len(cluster_list[fix_cluster]):
				try:
					if "virtual_row_nr" in cluster_list[fix_cluster][fix_record]:
						cluster_list[fix_cluster].pop(fix_record)
					# add split for marriage
					elif "split_for_detecting_marriage" in cluster_list[fix_cluster][fix_record]:
						#cluster_list[fix_cluster][fix_record]["matching"] += cluster_list[fix_cluster][fix_record]["split_for_detecting_marriage"]
						#del cluster_list[fix_cluster][fix_record]["split_for_detecting_marriage"]
						fix_record += 1
					else:	
						cluster_list[fix_cluster][fix_record]["split_for_detecting_marriage"] = ""
						fix_record += 1
				except:
					fix_record += 1
					pass

		#cannot remove clusters only consisting of virtual records, because the cluster_list is a dict. If all records in a cluster is removed, then it's a empty cluster, which does not affect anything.
		# all keys in cluster_list after removing the empty cluster: key - 1 table_07 02

	def _remove_empty_cluster(self, cluster_list):
		''' some cluster could be empty because the records were moved into other clusters
		'''
		for cluster in range(len(sorted(cluster_list))):
			# in case cluster does not exist
			try:
				if len(cluster_list[cluster]) < 1:
					#print(cluster,"is empty")
					del cluster_list[cluster]
			except:
				pass

		# renumber clusters
		cluster_list_temp = {}
		cluster_renumber = 0
		for cluster in sorted(cluster_list):
			cluster_list_temp[cluster_renumber] = cluster_list[cluster]
			for record in range(len(cluster_list_temp[cluster_renumber])):
				cluster_list_temp[cluster_renumber][record]["cluster"] = cluster_renumber
				if not self._detect_marriages:
					cluster_list_temp[cluster_renumber][record]["split_for_detecting_marriage"] = None
			cluster_renumber += 1
		cluster_list.clear()
		#print("cleared:",cluster_list)
		for renamed_cluster in sorted(cluster_list_temp):
			cluster_list[renamed_cluster] = cluster_list_temp[renamed_cluster]
		#for x in cluster_list:
			#print("reloaded:",x,cluster_list[x])
		#for x in cluster_list_temp: 
		#	print(x, cluster_list_temp[x])

	def _save_to_file(self, cluster_list, output_format, file_name, name_table_format):
		''' Save cluster_list to csv or to authors table in a database
		'''

		##########################################
		# Transform to list of dicts table structure
		# Initialize output
		output_data = self._make_flat_result(cluster_list, name_table_format)

		# Recognize format, if none given
		if output_format is None:
			if "xls" in file_name:
				output_format = "xls"
			else:
				output_format = "csv"

		########################################
		# Save the structure to output format

		# If output to csv file
		if output_format=="csv":
			# Check if file extension is ".csv" and attach this string otherwise
			if file_name[-1:]=="/" or file_name[-1:]=="\\" or file_name=="":
				file_name="persons.csv"
			elif file_name[-4:]!=".csv":
				file_name += ".csv"
			# Get the file
			csvWriter = csv.writer(open(file_name, 'w'), lineterminator='\n')
			# First write column headers
			csvWriter.writerow( list(output_data[0].keys()) )
			# Write data
			for i in range( len(output_data) ):
				csvWriter.writerow([output_data[i][k] for k in output_data[i] ])
		# If output to csv file
		if output_format=="xls":
			try:
				import pandas as pd
			except:
				print("Requires 'pandas' to export as xlsx.")
				return
			# Check if file extension is ".csv" and attach this string otherwise
			if file_name[-1:]=="/" or file_name[-1:]=="\\" or file_name=="":
				file_name="persons.xlsx"
			elif file_name[-4:]!=".xlsx":
				file_name += ".xlsx"
			# Get the file
			xlsWriter = pd.ExcelWriter(file_name)
			# Convert output to pandas DataFrame
			df = self._convert_records_to_pandas(output_data)
			# First write column headers
			df.to_excel(xlsWriter, "persons")
			xlsWriter.save()

	def _make_flat_result(self, cluster_list, name_table_format):
		''' Flaten cluster_list to list of records
		'''

		##########################################
		# Transform to list of dicts table structure
		# Initialize output
		output_data = []
		processed_time = datetime.now(self._tz)
		processed_time_string = processed_time.strftime(self._fmt)
		# Iterate over all clusters
		for i_cluster in cluster_list:
			for record in cluster_list[i_cluster]:
				# Compile table of the output data
				matching_code = "equal"
				if "vertical" in record["matching"]:
					matching_code = "vertical"
				if "interlaced" in record["matching"]:
					matching_code = "interlaced"
				output_data 		.append( collections.OrderedDict([
												("person_id" 										, record["cluster"] 									),
												# ("fnm_normalized"									, record["fnm_normalized"] 								),
												# ("snm_normalized"									, record["snm_normalized"] 								),
												("source"											, record["source"] 										),
												(name_table_format["columns"]["id_column"]			, record["id"] 											),
												(name_table_format["columns"]["fnm_column"]			, record["fnm"] 										),
												(name_table_format["columns"]["snm_column"]			, record["snm"] 										),
												("matching" 										, matching_code 								 		),
												("saving_time"										, processed_time_string 								)
										]) )
				if "year" in record.keys():
					output_data[-1][name_table_format["columns"]["year_column"]] 					= record["year"]
				if "mnm" in record.keys():
					output_data[-1][name_table_format["columns"]["mnm_column"]] 					= record["mnm"]
				if "maximum_time_gap" in record.keys():
					output_data[-1]["maximum_time_gap"] 											= record["maximum_time_gap"]
				if self._detect_marriages:
					output_data[-1]["detecting_marriage"] 											= record["split_for_detecting_marriage"]

		return output_data

	def _convert_records_to_pandas(self, in_data):
		import pandas as pd
		return pd.DataFrame( collections.OrderedDict( [ ( key , [ elem[key] for elem in in_data ] ) for key in in_data[0].keys() ] ) )

	def _find_node_by_name(self, names, snm, fnm):
		''' Find the node number for a given name in the tree 'names'
		'''
		try:
			for index_record in range( len(names[snm]["records"]) ):
				if names[snm]["records"][index_record]["fnm_normalized"]==fnm:
					return names[snm]["node_by_record"][index_record]
		except:
			pass
		return -1

	def _identify_cols(self, table, source_type):
		forename_identifiers = ["fore", "first", "fnm", "given", "christian", "baptism", "baptismal"] # http://www.thesaurus.com/browse/first-name
		surname_identifiers = ["sur", "last", "snm", "family", "cognomen", "byname", "matronymic", "patronymic", "metronymic"] # http://www.thesaurus.com/browse/surname
		middlename_identifiers = ["middle", "initial", "second"]
		year_identifiers = ["year", "yr"]
		id_identifiers = ["id"]

		colnames = table[0].keys()

		# If no middle name
		name_format = "fnm and snm"
		year_column = None
		mnm_column = None
		id_column = None

		for colname in colnames:
			colname_norm = normalize(colname).replace(" ", "")
			if any([(x in colname_norm) for x in forename_identifiers]):
				fnm_column = colname
			elif any([(x in colname_norm) for x in surname_identifiers]):
				snm_column = colname
			elif any([(x in colname_norm) for x in middlename_identifiers]):
				mnm_column = colname
				name_format = "fnm, middle and snm"
			elif any([(x in colname_norm) for x in year_identifiers]):
				year_column = colname
			elif any([(x in colname_norm) for x in id_identifiers]):
				id_column = colname

		if fnm_column is None:
			print("Error: Forename column missing! Please provide a column titled 'forename'.")
		if snm_column is None:
			print("Error: Surname column missing! Please provide a column titled 'surname'.")

		return	{
					"name_format" 		: name_format,
					"source_type" 		: source_type,
					"columns" 			: {
						"id_column" 		: id_column,
						"snm_column" 		: snm_column,
						"fnm_column" 		: fnm_column,
						"mnm_column" 		: mnm_column,
						"year_column" 		: year_column 
						}
				}

	def _add_id_col(self, table):
		count = 0
		for record in table:
			record["name_id"] = count
			count += 1

	def _add_empty_col(self, table, col_name):
		for record in table:
			record[col_name] = ""

	def _convert_table_to_records(self, in_data, format):
		if format=="pandas":
			return in_data.to_dict("records")
		if format=="csv":
			import csv
			# Get the file
			csvReader = csv.DictReader(open(in_data, 'r'))
			return [ row for row in csvReader ]
		if format=="xls":
			try:
				import pandas as pd
			except:
				print("Requires 'pandas' to export as xlsx.")
				return
			# Get the file
			df = pd.read_excel(in_data)
			return df.to_dict("records")

	##########################################################
	### Public functions ################################

	def plot_persons(self, snm, fnm, selection="interrelated"):
		''' 
		Draw a graph depicting the relationships between the names.
		'''

		if self._flat_tree is None:
			print("Before plotting a graph, first process a table of names through the 'persons_from_names' function.")
			return

		names = self._flat_tree

		snm 						= normalize(snm)
		fnm 						= normalize(fnm)
		start_node 					= self._find_node_by_name(names, snm, fnm)
		if start_node!=-1:
			# Reference to the records_by_node mapping
			records_by_node 		= names[snm]["records_by_node"]
			# Process all nodes
			to_be_processed 		= list( range( len(records_by_node) ) )
			# Move given node to the beginning
			to_be_processed 		. remove(start_node)
			to_be_processed 		= [start_node] + to_be_processed
			# Find relevant set of nodes
			if selection=="interrelated":
				nodes 				= self._find_interrelated(names, snm, to_be_processed, ["identical", self._me_subset, self._it_subset, "crossed"])
			elif selection=="vertical":
				nodes 				= self._find_interrelated(names, snm, to_be_processed, ["identical", self._me_subset, self._it_subset])
			elif selection=="all":
				nodes 				= to_be_processed

			# Node names
			node_names 				= set()

			# Graph (create from adjacency matrix)
			G 						= Graph(names[snm]["matrix"], list(nodes))

			# Transitive reduction
			G 						. transitive_reduction()

			# Get top nodes sorted by first name
			G 						. set_top_nodes()
			top_nodes 				= [names[snm]["records"][ records_by_node[x][0] ]["fnm_normalized"] for x in G.top_nodes]
			top_nodes 				= sorted(top_nodes)
			top_nodes.reverse()
			G.top_nodes_sorted		= [self._find_node_by_name(names, snm, x) for x in top_nodes]

			# Get positions for a tree like layout
			positions 				= G.get_node_positions() 

			matrix 					= G.matrix

			edges 					= []
			vertical_edges 			= []
			crossed_edges 			= []
			labels 					= []
			# Node positions with the right coding (names, instead of number)
			node_positions 			= {}
			# Iterate over all edges
			for first in nodes:
				for second in nodes:
					# Extract first name of the first and second node
					fnm_first 	= names[snm]["records"][ records_by_node[first][0] ]["fnm"]
					fnm_second 	= names[snm]["records"][ records_by_node[second][0] ]["fnm"]
					# If the nodes are in a subset relationship
					if matrix[first][second] in [self._me_subset, self._it_subset] and (fnm_second, fnm_first) not in vertical_edges:
						edges.append( (fnm_first, fnm_second) )
						vertical_edges.append( (fnm_first, fnm_second) )
						labels.append( "subset" )
						node_positions[fnm_first] 		= positions[first]
						node_positions[fnm_second] 		= positions[second]
						node_names.add(fnm_first)
						node_names.add(fnm_second)
					# If the nodes are in a non-transitive relationship
					elif matrix[first][second]=="crossed" and (fnm_second, fnm_first) not in crossed_edges:
						edges.append( (fnm_first, fnm_second) )
						crossed_edges.append( (fnm_first, fnm_second) )
						labels.append( "interlaced" )
						node_positions[fnm_first] 		= positions[first]
						node_positions[fnm_second] 		= positions[second]
						node_names.add(fnm_first)
						node_names.add(fnm_second)
			# Draw the graph
			draw_graph(nodes=list(node_names), edges=edges, vertical_edges=vertical_edges, crossed_edges=crossed_edges, labels=labels, node_positions=node_positions)
		else:
			print("Name not found.")

	def persons_from_names(self, name_table, known_persons=None, output_file=None, output_file_format=None, status_messages=True):
		"""
		Identify persons in a table of names.
		Check the file "examples.py" for usage examples.
		Parameters:
			- name_table: 			table of names (and potentially years)
									-> Supported input formats presently include:
										-- "records" (default, list of dicts or OrderedDicts, e.g. returned by SQL query)
										-- "pandas" (pandas DataFrame)
			  						-> accepts file path
			  						-> the following file formats are supported
			  							-- "csv" (csv file, requires additional parameter "path_name_table") 
										-- "xls" (Excel file, requires additional parameter "path_name_table")
			- known_persons: 		table of names of known unique persons who have been identified previously
									-> accepts file path if input_format="csv" or input_format="xls"
			- output_file 			path for saving result in a file
			- output_file_format: 	supported output file formats presently include
									-- "csv" (default)
									-- "xls"
		"""

		# Save start time:
		zeit=int(time.time())

		####
		## Prepare input table
		####

		# Recognize input format
		if "pandas" in str(type(name_table)):
			input_format = "pandas"
		elif "list" in str(type(name_table)):
			input_format = "records"
		elif "str" in str(type(name_table)):
			if ".csv" in name_table:
				input_format = "csv"
			elif "xls" in name_table:
				input_format = "xls"

		# Convert table to internal data format
		if input_format != "records":
			name_table = self._convert_table_to_records(name_table, input_format)

		# Identify forename col
		name_table_format = self._identify_cols(name_table, "default table")

		# Add id column if missing
		if name_table_format["columns"]["id_column"] is None:
			self._add_id_col(name_table)
			name_table_format["columns"]["id_column"]="name_id"

		# Same as above for known persons table
		if known_persons is not None:
			# Convert table to internal data format
			if input_format != "records":
				known_persons = self._convert_table_to_records(known_persons, input_format)

			# Identify forename col
			known_persons_format = self._identify_cols(known_persons, self._table_with_unique_names)

			if known_persons_format["columns"]["id_column"] is None:
				self._add_id_col(known_persons)
				known_persons_format["columns"]["id_column"]="name_id"

			if known_persons_format["columns"]["year_column"] is None:
				self._add_empty_col(known_persons, "year")
				known_persons_format["columns"]["year_column"]="year"

		####
		## Sort input data into a tree structure according to surname
		####

		# Internal data structure by surname
		self._flat_tree=collections.OrderedDict()

		if status_messages:
			print("Tree creation in progress...")
		self._make_flat_tree(name_table, self._flat_tree, name_table_format)
		if known_persons is not None:
			# Identify forename col
			self._make_flat_tree(known_persons, self._flat_tree, known_persons_format)

		####
		## Person identification from forename
		####

		if status_messages:
			print("Clustering in progress...")
		cluster_list={}
		self._cluster_number = 0

		# to record in which clusters the original records and their virtual ones are assigned 
		cluster_number_list = {}
		self._cluster(self._flat_tree, cluster_list, cluster_number_list)

		if self._split_by_time_gap and name_table_format["columns"]["year_column"] is not None:
			if status_messages:
				print(format("Splitting entries with more than {} years between chronologically succeeding entries...", self._maximum_time_gap))
			self._time_gap(cluster_list, self._maximum_time_gap, cluster_number_list, action="split")

		if self._detect_marriages:
			if status_messages:
				print("Detecting marriages and combining entries with marriage-related surname change...")
			self._rework_for_marriages(cluster_list, cluster_number_list)

		if self._empty_clusters_remove:
			if status_messages:
				print("Tidying up...")
			self._remove_empty_cluster(cluster_list)

		####
		## Processing results
		####

		# Save authors to file 
		if output_file is not None:
			if status_messages:
				print("Saving the results")
			self._save_to_file(cluster_list, output_file_format, output_file, name_table_format)

		# if status_messages:
		# 	print( "Name matching completed in {} seconds. Identified {} persons.".format( str( int(time.time()) - zeit ) , str(len(cluster_list)) ) )

		if input_format=="pandas":
			return self._convert_records_to_pandas(self._make_flat_result(cluster_list, name_table_format))
		elif input_format=="records" and "dict" in str(type(name_table[0])):
			return [ dict(record) for record in self._make_flat_result(cluster_list, name_table_format) ]
		else:
			return self._make_flat_result(cluster_list, name_table_format)



