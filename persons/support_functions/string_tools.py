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

# -*- coding: utf-8 -*-
import re

def remove_particles(string):
	''' Remove noble particles and suffixes (for last names).
		Only remove, if the name doesn't become empty.
	'''

	if len(string.split(" "))>1:
		# Particles to be removed
		particles 	= ["van", "von", "de", "d", "di", "dei", "of", "zu", "zur", "dos", "af", "der", "graf"]
		
		transformed = string
		for particle in particles:
			transformed 	= re.sub(r"\b%s\b" % particle, '', transformed)

		transformed = transformed.strip()

		if len(transformed.split(" "))>0 and transformed!="":
			return transformed
		return string
	return string

def normalize(string):
	''' Remove evil characters from names and replace with another character.
	'''

	if string==None:
		return ""
	else:
		# To lower case:
		string = string.lower()

		invalid = 	{
					'Š' : 'S', 
					'š' : 's', 
					'Ð' : 'Dj', 
					'd' : 'd', 
					'Ž' : 'Z', 
					'ž' : 'z', 
					'C' : 'C', 
					'c' : 'c', 
					'C' : 'C', 
					'c' : 'c', 
					'À' : 'A', 
					'Á' : 'A', 
					'Â' : 'A', 
					'Ã' : 'A', 
					'Ä' : 'A', 
					'Å' : 'A', 
					'Æ' : 'A', 
					'Ç' : 'C', 
					'È' : 'E', 
					'É' : 'E', 
					'Ê' : 'E', 
					'Ë' : 'E', 
					'Ì' : 'I', 
					'Í' : 'I', 
					'Î' : 'I', 
					'Ï' : 'I', 
					'Ñ' : 'N', 
					'Ò' : 'O', 
					'Ó' : 'O', 
					'Ô' : 'O', 
					'Õ' : 'O', 
					'Ö' : 'O', 
					'Ø' : 'O', 
					'Ù' : 'U', 
					'Ú' : 'U', 
					'Û' : 'U', 
					'Ü' : 'U', 
					'Ý' : 'Y', 
					'Þ' : 'B', 
					'ß' : 'Ss', 
					'à' : 'a', 
					'á' : 'a', 
					'â' : 'a', 
					'ã' : 'a', 
					'ä' : 'a', 
					'å' : 'a', 
					'æ' : 'a', 
					'ç' : 'c', 
					'è' : 'e', 
					'é' : 'e', 
					'ê' : 'e', 
					'ë' : 'e', 
					'ì' : 'i', 
					'í' : 'i', 
					'î' : 'i', 
					'ï' : 'i', 
					'ð' : 'o', 
					'ñ' : 'n', 
					'ò' : 'o', 
					'ó' : 'o', 
					'ô' : 'o', 
					'õ' : 'o', 
					'ö' : 'o', 
					'ø' : 'o', 
					'ù' : 'u', 
					'ú' : 'u', 
					'û' : 'u', 
					'ü' : 'u', 
					'ý' : 'y', 
					'ý' : 'y', 
					'þ' : 'b', 
					'ÿ' : 'y', 
					'R' : 'R', 
					'r' : 'r', 
					"`"  :  "", 
					"´"  :  "", 
					"„"  :  "", 
					"`"  :  "", 
					"´"  :  "", 
					"“"  :  "", 
					"”"  :  "", 
					"´"  :  "", 
					"&acirc;€™"  :  "", 
					"{"  :  "", 
					"~"  :  "", 
					"–"  :  " ", 
					"’"  :  "", 
					"\""  :  "", 
					"'"  :  "", 
					"-"  :  " ", 
					"."  :  " ", 
					":" : " ", 
					"("  :  "", 
					")"  :  "", 
					"{"  : "", 
					"}" : "", 
					"[" : "", 
					"]" : "", 
					"/" : " ", 
					"\\" : " ", 
					"|" : " ", 
					":" : " ", 
					"*" : " ", 
					"&" : " and "
				}

		# Remove numbers and replace invalid expressions
		string = ''.join( (c if c not in invalid else invalid[c]) for c in string if not c.isdigit())

		# Trim inner part of the string by replacing multiple succeeding white space by only one
		return re.sub('\s+', ' ', string).strip()

