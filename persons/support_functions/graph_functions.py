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

class Graph:
	''' Graph defined by matrix with transitive reduction (minimum equivalent graph) function
	'''

	# Construct graph
	def __init__(self, matrix, nodes):
		self.nodes                      = nodes
		self.matrix                     = matrix.copy()
		self.top_nodes                  = set()                     # Filled if required, using top_nodes() function
		self.top_nodes_sorted 			= []
		it_subset                       = 1
		me_subset                       = -1
		self.main_direction             = it_subset
		self.main_direction_backwards   = me_subset

	def transitive_reduction(self):
		self.edges_to_remove = []
		for x in self.nodes:
			for y in self.nodes:
				for z in self.nodes:
					if (x,y) != (y,z) and (x,y) != (x,z):
						if self.matrix[x][y]==self.main_direction and self.matrix[y][z]==self.main_direction:
							self.edges_to_remove.append( [x,z] )

		for edge in self.edges_to_remove:
			self.matrix[edge[0]][edge[1]]=0
			self.matrix[edge[1]][edge[0]]=0

	def set_top_nodes(self):
		for node in self.nodes:
			if self.main_direction_backwards not in self.matrix[node]:
				self.top_nodes.add(node)

	def get_single_strands_rec(self, completed_strands, current_strand, current_node):
		# If the new node has multiple predecessors
		if self.matrix[current_node].count(self.main_direction_backwards)>1:
			# Add previous strand to completed
			if len(current_strand)>0:
				completed_strands.append(current_strand)
			# Current node is a single strand, because it's a forking node
			completed_strands.append([current_node])
			# Look at each fork
			for next_node in range( len(self.matrix[current_node]) ):
				if self.matrix[current_node][next_node]==self.main_direction:
					# Start new strand for the fork
					self.get_single_strands_rec( completed_strands, [], next_node )
		# Strand splits into multiple substrands
		elif self.matrix[current_node].count(self.main_direction)>1:
			# Add previous strand to completed
			if len(current_strand)>0:
				completed_strands.append(current_strand)
			# Current node is a single strand, because it's a forking node
			completed_strands.append([current_node])
			# Look at each fork
			for next_node in range( len(self.matrix[current_node]) ):
				if self.matrix[current_node][next_node]==self.main_direction:
					# Start new strand for the fork
					self.get_single_strands_rec( completed_strands, [], next_node )
		# Strand continues with exactly one member
		elif self.matrix[current_node].count(self.main_direction)==1:
			# Add current node to the existing strand
			self.get_single_strands_rec( completed_strands, current_strand+[current_node], self.matrix[current_node].index(self.main_direction) )
		# Final member of the strand
		else:
			# Append completed strand to completed_strands
			completed_strands.append(current_strand+[current_node])

	def get_single_strands(self):
		# Compute top nodes
		self.set_top_nodes()
		# Create list for the completed strands
		self.completed_strands              = []
		# Start a strand at each top node
		for node in self.top_nodes:
			self.get_single_strands_rec(self.completed_strands,[],node)
		# Uniquefy
		self.completed_strands = [str(x) for x in self.completed_strands]
		self.completed_strands = set(self.completed_strands)
		self.completed_strands = [eval(x) for x in self.completed_strands]
		# Return the result
		return self.completed_strands.copy()

	def get_node_positions_rec(self, node_positions, frame_coordinates, current_node):
		''' Iterate from given node to the bottom of the tree
		'''
		# If the new node has been processed already
		if current_node in node_positions.keys():
			# Ignore the node, break recursion
			return
		# If the node has not been processed yet, assign coordinates
		else:
			node_positions[current_node] 	= (frame_coordinates["current_right"], frame_coordinates["current_bottom"])

		# Continue with next node
		# If strand has successors
		if self.matrix[current_node].count(self.main_direction)>0:
			# Next level lower than last level
			frame_coordinates["current_bottom"] 		-=10
			frame_coordinates["current_right"] 			= frame_coordinates["outer_right"]
			current_right 								= frame_coordinates["current_right"]
			current_bottom 								= frame_coordinates["current_bottom"]
			# Look at each fork
			for next_node in range( len(self.matrix[current_node]) ):
				if self.matrix[current_node][next_node]==self.main_direction:
					# Start new strand for the fork
					self.get_node_positions_rec( node_positions, frame_coordinates, next_node )
					# Next level further right than last level
					frame_coordinates["current_right"] 	+=10
			frame_coordinates["current_right"] 			-=10
			frame_coordinates["outer_right"] 			= frame_coordinates["current_right"]
		# Final member of the strand
		else:
			return

	def get_node_positions(self):
		''' Get positions of nodes to align them in a tree-like graph 
		'''
		# Create list for the completed strands
		self.node_positions 			= {}
		# Coordinates of the frame of the graph
		self.frame_coordinates 			= {"outer_right": 0, "initial_bottom": 0, "current_right": 0, "current_bottom": 0}
		# Start at each top node
		for node in self.top_nodes_sorted:
			self.frame_coordinates["current_bottom"]= self.frame_coordinates["initial_bottom"]
			self.frame_coordinates["current_right"] = self.frame_coordinates["outer_right"]
			self.get_node_positions_rec(self.node_positions, self.frame_coordinates, node)
			self.frame_coordinates["outer_right"] 	+=10
			self.frame_coordinates["current_right"] = self.frame_coordinates["outer_right"]
			if self.frame_coordinates["initial_bottom"]==0:
				self.frame_coordinates["initial_bottom"]= -1
			else:
				self.frame_coordinates["initial_bottom"]= 0
		# Return the result
		return self.node_positions.copy()

# # Script for testing Graph class
# a = [
# 	  ['identical', 'crossed', 1, 'crossed', 1], 
# 	  ['crossed', 'identical', 'crossed', 1, 1], 
# 	  [-1, 'crossed', 'identical', 'different', 1], 
# 	  ['crossed', -1, 'different', 'identical', 'different'], 
# 	  [-1, -1, -1, 'different', 'identical']
#   ]

# G = Graph(a, [0,1,2,3,4])

# G.transitive_reduction()

# G.top_nodes
# import pprint
# print("Removed edges:")
# pprint.pprint(G.edges_to_remove)
# print("Remaining edges:")
# pprint.pprint(G.matrix)
# print("Top nodes:")
# G.set_top_nodes()
# pprint.pprint(G.top_nodes)
# print("Single strands:")
# single_strands=G.get_single_strands()
# pprint.pprint(single_strands)
# print("Positions")
# node_positions = G.get_node_positions() 
# print( node_positions )

def draw_graph(nodes, edges, vertical_edges=[], crossed_edges=[], labels=None, graph_layout='shell', node_positions=[],
node_size=2000, node_color='lightblue', node_alpha=0.3,
node_text_size=10,
edge_color='blue', edge_alpha=0.3, edge_tickness=1,
edge_text_pos=0.5,
text_font='sans-serif'):
	"""
	Plot graph
	"""
	try:
		import networkx as nx
	except:
		print("This package requires 'networkx' for plotting graphs.")
		return
	try:
		import matplotlib.pyplot as plt
	except:
		print("This package requires 'matplotlib' for plotting graphs.")
		return

	# create networkx graph
	G=nx.Graph()

	graph 		= edges

	# add edges
	for edge in graph:
		G.add_edge(edge[0], edge[1])

	# these are different layouts for the network you may try
	# shell seems to work best
	if len(node_positions)>0:
		graph_pos = node_positions
	elif graph_layout == 'spring':
		graph_pos=nx.spring_layout(G)
	elif graph_layout == 'spectral':
		graph_pos=nx.spectral_layout(G)
	elif graph_layout == 'random':
		graph_pos=nx.random_layout(G)
	else:
		graph_pos=nx.shell_layout(G)		

	# draw graph
	nx.draw_networkx_nodes(G,graph_pos,
							nodelist=nodes, node_size=node_size, 
						   alpha=node_alpha, node_color=node_color)

	nx.draw_networkx_edges(G,graph_pos,width=1.0,alpha=0.5)
	nx.draw_networkx_edges(G,graph_pos,
						   edgelist=vertical_edges,
						   width=8,alpha=0.5,edge_color='b')
	# nx.draw_networkx_edges(G,graph_pos,
	# 					   edgelist=crossed_edges,
	# 					   width=8,alpha=0.5,edge_color='r')

	nx.draw_networkx_labels(G, graph_pos,font_size=node_text_size,
							font_family=text_font)

	if labels is None:
		labels = range(len(graph))

	# Draw nodes again to cover the long edges
	nx.draw_networkx_nodes(G,graph_pos,
							nodelist=nodes, node_size=node_size, 
						   alpha=1, node_color=node_color)

	edge_labels = dict(zip(graph, labels))
	nx.draw_networkx_edge_labels(G, graph_pos, edge_labels=edge_labels, 
								 label_pos=edge_text_pos)

	# show graph
	plt.show()
