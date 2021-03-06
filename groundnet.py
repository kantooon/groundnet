#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Adrian Musceac 
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os, sys, glob, math
import io, multiprocessing
import re, string 

__doc__="""Experimental script to generate a ground network for default airports
Works on all airports which have the following 810 format: one runway,
one long taxiway along the runway, 3 short taxiways to the ends and the center
of the runway. 9 parking positions are also generated near the long taxiway.

First set path below to Airports directory inside the scenery directory.
Ground networks will be saved in the output directory inside the current directory

After the first run, a cache file named airport_list.txt or airport_list_850.txt
is created in the working directory, containing a list of all airports in the scenery
directory which are missing a ground network, regardless of the format of the airport.
This makes further runs of the script execute faster.

Version 0.2: The script now can parse v850 airports which fit the same default
format. To use the 850 parser you need a apt850.dat file in the working directory.
Ground networks will be saved in the output850 directory inside the current directory

Usage:
groundnet.py all -> generates all airports which fit the criteria
groundnet.py airport <ICAO> -> generates only one airport for the ICAO code provided

groundnet.py all 850 -> generates all airports from apt850.dat which fit the criteria
groundnet.py airport <ICAO> 850 -> generates only one airport for the ICAO code provided
"""

class Groundnet:
	def __init__(self,version=810):
		self.scenery_airports="/home/adrian/games/fgfs/terrasync/Airports/" # path to Airports directory inside scenery dir
		self.save_tree=True   # true if the generated files should be saved in a tree structure similar to the scenery one
		self.park_spacing=60  # space in meters between centers of parking positions
		self.park_distance=50 # space in meters between taxiway and parking pos. 
		self.default_airports=[]
		self.apt_index=[]
		self.missing_network=[]
		self.done_files=[]
		self.version=version
		if self.version==850:
			self.load_apt_850()
		else:
			self.load_apt()
		self.check_already_done()
		self.get_airport_list()
		
		self.apts = (set(self.default_airports) & set(self.missing_network)) - set(self.done_files)
		
		
	def get_airport_list(self):
		if self.version==850:
			airport_list='airport_list_850.txt'
		else:
			airport_list='airport_list.txt'
			
		try:
			os.stat(os.path.join(os.getcwd(),airport_list))
		except:
			os.path.walk(self.scenery_airports,self.check_groundnet,None)
			fw=open(os.path.join(os.getcwd(),airport_list),'wb')
			buf="\n".join(self.missing_network)
			fw.write(buf)
			fw.close()
			return
		
		fr=open(os.path.join(os.getcwd(),airport_list))
		content=fr.readlines()
		for line in content:
			self.missing_network.append(line.rstrip('\n'))
		fr.close()
		
	
	def parse_all(self):
		print "Airports to be processed:",len(self.apts)
		print "Airports with missing network:",len(self.missing_network), "Airports with known format:",len(self.default_airports)
		hh=0
		
		q=multiprocessing.Queue(10)
		for a in self.apts:
			hh+=1
			print a, len(self.apts) - hh,"left"
			#self.parse_airport( a)
			index=dict(self.apt_index)
			content=self.apt_content[index[a]-1:index[a]+40]
			q.put(hh)	
			pthread=Parser(a,self.save_tree,self.park_spacing,self.park_distance,content,self.version,q,hh)
			pthread.start()
			
			
	def parse_airport(self,a):
		q=multiprocessing.Queue(2)
		hh=1
		print apt
		q.put(hh)
		pthread=Parser(a,self.save_tree,self.park_spacing,self.park_distance,self.apt_content,self.version,q,hh)
		pthread.start()


	def load_apt(self):
		fr=open(os.path.join(os.getcwd(),'apt.dat'),'rb')
		content=fr.readlines()
		self.apt_content=content
		fr.close()
		i=0
		for line in content:
			if re.search("^1\s+",line)!=None:
				num_segs=0
				seg_len=[]
				for k in range(i+1,i+10):
					if content[k]=='\n' or content[k]=='\r\n':
						break
					if re.search("^10\s+.*?xxx\s+",content[k])!=None:
						data=content[k].split()
						seg_len.append(data[5])
						num_segs +=1
				if num_segs==4:
					if seg_len[0]==seg_len[1] and seg_len[0]==seg_len[2] and float(seg_len[0])<float(seg_len[3]) and float(seg_len[3])>=2000:
						match=re.search("^1\s+[0-9]+\s+[0-9]+\s+[0-9]+\s+([0-9A-Z]{3,5})\s+",line)
						if match!=None:
							if match.group(1) not in self.default_airports:
								self.default_airports.append(match.group(1))
								self.apt_index.append((match.group(1),i))
			i+=1
			
	
	def load_apt_850(self):
		fr=open(os.path.join(os.getcwd(),'apt850.dat'),'rb')
		content=fr.readlines()
		self.apt_content=content
		fr.close()
		i=0
		for line in content:
			if re.search("^1\s+",line)!=None:
				num_segs=0
				num_taxiways=0
				num_bezier=0
				num_holds=0
				seg_len=[]
				for k in range(i+1,i+40):
					if content[k]=='\n' or content[k]=='\r\n':
						break
					if re.search("^110\s+",content[k])!=None:
						num_taxiways +=1
					if re.search("^112\s+",content[k])!=None:
						num_bezier +=1
					if re.search("^120\s+",content[k])!=None:
						num_holds +=1
					if re.search("^111\s+",content[k])!=None:
						data=content[k].split()
						#seg_len.append(data[5])
						num_segs +=1
				if num_segs==14 and num_taxiways==1 and num_bezier==4 and num_holds==3:
					#if seg_len[0]==seg_len[1] and seg_len[0]==seg_len[2] and float(seg_len[0])<float(seg_len[3]) and float(seg_len[3])>=2000:
					match=re.search("^1\s+[0-9]+\s+[0-9]+\s+[0-9]+\s+([0-9A-Z]{3,5})\s+",line)
					if match!=None:
						if match.group(1) not in self.default_airports:
							self.default_airports.append(match.group(1))
							self.apt_index.append((match.group(1),i))
			i+=1
		
		
	def check_already_done(self):
		if self.version==850:
			output_dir='output850'
		else:
			output_dir='output'
		if self.save_tree==False:
			done_files1=glob.glob(os.path.join(os.getcwd(),output_dir,'*.xml'))
		else:
			done_files1=glob.glob(os.path.join(os.getcwd(),output_dir,'Airports','*','*','*','*.xml'))
			
		for d in done_files1:
			icao1=d.split('.')
			icao=icao1[0].split('/')
			if icao[-1] not in self.done_files:
				self.done_files.append(icao[-1])
			
		
		
	def check_groundnet(self,arg,dirname,filenames):
		if dirname.find(".svn")!=-1:
			return
		found_files=False
		icao_list=[]
		for filename in filenames:
			if re.search(".xml",filename)!=None:
				found_files=True
				tokens=filename.split(".")
				if os.path.exists(os.path.join(dirname,tokens[0]+".groundnet.xml")):
					continue
				if os.path.exists(os.path.join(dirname,tokens[0]+".parking.xml")):
					continue
				else:
					if tokens[0] not in self.missing_network:
						self.missing_network.append(tokens[0])
	
		
class Parser(multiprocessing.Process):
	
	def __init__(self,apt,tree,park_spacing,park_distance,content,version,q,hh):
		multiprocessing.Process.__init__(self)
		self.apt=apt
		self.save_tree=tree
		self.park_spacing=park_spacing
		self.apt_content=content
		self.q=q
		self.ids=hh
		self.park_distance=park_distance
		self.version=version
		
	
	def run(self):
		if self.version == 850:
			self.parse_airport_850(self.apt)
		else:
			self.parse_airport(self.apt)
		self.q.get(self.ids)
		
	########## 810 #############	
	def parse_airport(self,apt):
		xml=[]
		xml.append('<?xml version="1.0"?>\n<groundnet>\n<version>1</version>\n<frequencies>\n')
		content=self.apt_content
		i=0
		line_data=[]
		freq_data=[]
		
		for line in content:
			if re.search("^1\s+[0-9]{1,7}\s+[0-9]{1}\s+[0-9]{1}\s+"+apt+"\s+",line)!=None:
				for k in range(i+1,i+15):
					if content[k]=='\n' or content[k]=='\r\n':
						break
					if re.search("^10\s+.*?xxx\s+",content[k])!=None:
						line_data.append(content[k])
				for z in range(i+4,i+25):
					if content[z]=='\n':
						break
					if re.search("^5[0-9]{1}\s+([0-9]{5})\s+",content[z])!=None:
						freq_data.append(content[z])
			i+=1
			
		
		for ln in freq_data:
			freq=ln.split()
			if freq[0]=='50':
				xml.append('\t<AWOS>'+freq[1]+'</AWOS>\n')
			if freq[0]=='51':
				xml.append('\t<UNICOM>'+freq[1]+'</UNICOM>\n')
			if freq[0]=='52':
				xml.append('\t<CLEARANCE>'+freq[1]+'</CLEARANCE>\n')
			if freq[0]=='53':
				xml.append('\t<GROUND>'+freq[1]+'</GROUND>\n')
			if freq[0]=='54':
				xml.append('\t<TOWER>'+freq[1]+'</TOWER>\n')
			if freq[0]=='55':
				xml.append('\t<APPROACH>'+freq[1]+'</APPROACH>\n')
			if freq[0]=='56':
				xml.append('\t<APPROACH>'+freq[1]+'</APPROACH>\n')
				
		xml.append('</frequencies>\n')
		nodes=[]
		subnodes=[]
		park=[]
		tt=0
		index=8
		
		for line in line_data:
			tt+=1
			METER_TO_NM=0.0005399568034557235
			NM_TO_RAD=0.00029088820866572159
			FEET_TO_METER=0.3048
			tokens = line.split()
			lat = float(tokens[1])
			lon = float(tokens[2])
			heading = float(tokens[4])
			heading_back=heading+180.0
			if heading_back>=360.0:
				heading_back=heading_back-360.0
			length = float(tokens[5]) * FEET_TO_METER / 2
			width = float(tokens[7])
			# lat=asin(sin(lat1)*cos(d)+cos(lat1)*sin(d)*cos(tc))
			#lon=mod(lon1-asin(sin(tc)*sin(d)/cos(lat))+pi,2*pi)-pi
			
			length_rad= length * METER_TO_NM * NM_TO_RAD
			
			lat1=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading))))
			lon1=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading))*math.sin(length_rad)/math.cos(math.radians(lat1))) + math.pi,2*math.pi)-math.pi)
			
			lat_end=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading_back))))
			lon_end=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading_back))*math.sin(length_rad)/math.cos(math.radians(lat_end))) + math.pi,2*math.pi)-math.pi)
			
			index+=1
			nodes.append((lat1,lon_end,index))
			index+=1
			nodes.append((lat,lon,index))
			index+=1
			nodes.append((lat_end,lon1,index))
			#print lat,lat1,lat_end,lon,lon1,lon_end
			
			if length > 300:
				xml.append('<parkingList>')
				yy=0
				for i in range(1,10):
					length_rad= self.park_spacing * i * METER_TO_NM * NM_TO_RAD
					lat2=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading))))
					lon2=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading))*math.sin(length_rad)/math.cos(math.radians(lat2))) + math.pi,2*math.pi)-math.pi)
					lat2_end=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading_back))))
					lon2_end=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading_back))*math.sin(length_rad)/math.cos(math.radians(lat2_end))) + math.pi,2*math.pi)-math.pi)
					length_rad2=self.park_distance * METER_TO_NM * NM_TO_RAD
					heading2=heading+90
					
					if(heading2>=360):
						heading2=heading2-360
						
					heading2_back=heading2 +180
					if heading2_back >=360:
						heading2_back=heading2_back-360
						
					lat3=math.degrees(math.asin(math.sin(math.radians(lat2))*math.cos(length_rad2)+math.cos(math.radians(lat2))*math.sin(length_rad2)*math.cos(math.radians(heading2))))
					lon3=math.degrees(math.fmod(math.radians(lon2_end)-math.asin(math.sin(math.radians(heading2))*math.sin(length_rad2)/math.cos(math.radians(lat3))) + math.pi,2*math.pi)-math.pi)
					
					lat3_end=math.degrees(math.asin(math.sin(math.radians(lat2))*math.cos(length_rad2)+math.cos(math.radians(lat2))*math.sin(length_rad2)*math.cos(math.radians(heading2_back))))
					lon3_end=math.degrees(math.fmod(math.radians(lon2_end)-math.asin(math.sin(math.radians(heading2_back))*math.sin(length_rad2)/math.cos(math.radians(lat3_end))) + math.pi,2*math.pi)-math.pi)
					
					xml.append(self.gen_parking(lat3,lon3_end,yy,heading2_back))
					park.append((lat3,lon3,yy))
					index+=1
					subnodes.append((lat2,lon2_end,index))
					yy+=1
					
					
				xml.append('\n</parkingList>\n')
			
			
		xml.append('<TaxiNodes>\n')
		#print len(nodes)
		#print len(subnodes)
		#print len(park)
		for n in nodes:
			coord=self.convert_coord(n[0],n[1])
			onrunway='0'
			hold='none'
			if n[2]==11 or n[2]==14 or n[2]==17:
				onrunway='1'
			if n[2]==10 or n[2]==13 or n[2]==16:
				hold='normal'
				
			xml.append('\t<node index="'+str(n[2])+'" lat="'+coord[0]+'" lon="'+coord[1]+'" isOnRunway="'+onrunway+'" holdPointType="'+hold+'" />\n')
			
			
		for n in subnodes:
			coord=self.convert_coord(n[0],n[1])
			xml.append('\t<node index="'+str(n[2])+'" lat="'+coord[0]+'" lon="'+coord[1]+'" isOnRunway="0" holdPointType="none" />\n')
			
		
		xml.append('</TaxiNodes>\n<TaxiWaySegments>\n')
		
		qq=0
		for p in park:
			xml.append('\t<arc begin="'+str(p[2])+'" end="'+str(subnodes[qq][2])+'" isPushBackRoute="0" name="" />\n')
			xml.append('\t<arc begin="'+str(subnodes[qq][2])+'" end="'+str(p[2])+'" isPushBackRoute="0" name="" />\n')
			qq+=1
		
		xml.append('\t<arc begin="'+str(nodes[0][2])+'" end="'+str(nodes[1][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[1][2])+'" end="'+str(nodes[0][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[1][2])+'" end="'+str(nodes[2][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[2][2])+'" end="'+str(nodes[1][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[0][2])+'" end="'+str(nodes[11][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[11][2])+'" end="'+str(nodes[0][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[11][2])+'" end="'+str(nodes[10][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[10][2])+'" end="'+str(nodes[11][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[10][2])+'" end="'+str(subnodes[0][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(subnodes[0][2])+'" end="'+str(nodes[10][2])+'" isPushBackRoute="0" name="" />\n')
		
		pp=0
		for s  in subnodes:
			if pp > len(subnodes)-2:
				break
			xml.append('\t<arc begin="'+str(s[2])+'" end="'+str(subnodes[pp+1][2])+'" isPushBackRoute="0" name="" />\n')
			xml.append('\t<arc begin="'+str(subnodes[pp+1][2])+'" end="'+str(s[2])+'" isPushBackRoute="0" name="" />\n')
			pp+=1
		
		
		
		xml.append('\t<arc begin="'+str(nodes[9][2])+'" end="'+str(subnodes[-1][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(subnodes[-1][2])+'" end="'+str(nodes[9][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[10][2])+'" end="'+str(nodes[3][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[3][2])+'" end="'+str(nodes[10][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[3][2])+'" end="'+str(nodes[4][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[4][2])+'" end="'+str(nodes[3][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[4][2])+'" end="'+str(nodes[5][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[5][2])+'" end="'+str(nodes[4][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[6][2])+'" end="'+str(nodes[9][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[9][2])+'" end="'+str(nodes[6][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[6][2])+'" end="'+str(nodes[7][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[7][2])+'" end="'+str(nodes[6][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(nodes[7][2])+'" end="'+str(nodes[8][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(nodes[8][2])+'" end="'+str(nodes[7][2])+'" isPushBackRoute="0" name="" />\n')
		
		
		
		xml.append('</TaxiWaySegments>\n</groundnet>\n')
		
		self.save_network(apt,xml)
		
	################ 850 #################
	def parse_airport_850(self,apt):
		xml=[]
		xml.append('<?xml version="1.0"?>\n<groundnet>\n<version>1</version>\n<frequencies>\n')
		content=self.apt_content
		i=0
		line_data=[]
		freq_data=[]
		heading=0
		
		for line in content:
			if re.search("^1\s+[0-9]{1,7}\s+[0-9]{1}\s+[0-9]{1}\s+"+apt+"\s+",line)!=None:
				for k in range(i+1,i+40):
					if content[k]=='\n' or content[k]=='\r\n':
						break
					if re.search("^111\s+",content[k])!=None:
						line_data.append(content[k])
					if re.search("^112\s+",content[k])!=None:
						line_data.append(content[k])
					if re.search("^113\s+",content[k])!=None:
						line_data.append(content[k])
					if re.search("^115\s+",content[k])!=None:
						line_data.append(content[k])
					if re.search("^110\s+[0-9.]+\s+[0-9.]+\s+([0-9.]+)\s+",content[k])!=None:
						tok=content[k].split()
						heading=float(tok[3])
				for z in range(i+4,i+40):
					if content[z]=='\n':
						break
					if re.search("^5[0-9]{1}\s+([0-9]{5})\s+",content[z])!=None:
						freq_data.append(content[z])
			i+=1
			
		
		for ln in freq_data:
			freq=ln.split()
			if freq[0]=='50':
				xml.append('\t<AWOS>'+freq[1]+'</AWOS>\n')
			if freq[0]=='51':
				xml.append('\t<UNICOM>'+freq[1]+'</UNICOM>\n')
			if freq[0]=='52':
				xml.append('\t<CLEARANCE>'+freq[1]+'</CLEARANCE>\n')
			if freq[0]=='53':
				xml.append('\t<GROUND>'+freq[1]+'</GROUND>\n')
			if freq[0]=='54':
				xml.append('\t<TOWER>'+freq[1]+'</TOWER>\n')
			if freq[0]=='55':
				xml.append('\t<APPROACH>'+freq[1]+'</APPROACH>\n')
			if freq[0]=='56':
				xml.append('\t<APPROACH>'+freq[1]+'</APPROACH>\n')
				
		xml.append('</frequencies>\n')
		nodes=[]
		subnodes=[]
		park=[]
		tt=0
		index=8
		
		for line in line_data:
			tt+=1
			METER_TO_NM=0.0005399568034557235
			NM_TO_RAD=0.00029088820866572159
			FEET_TO_METER=0.3048
			tokens = line.split()
			lat = float(tokens[1])
			if tokens[2]=='ASOS':
				print "error: ", apt
			lon = float(tokens[2])
			node_type = int(tokens[0])
			
			nodes.append((lat,lon,index))
		
		center1=self.find_midpoint(nodes[8][0],nodes[11][0],nodes[8][1],nodes[11][1],0)
		center2=self.find_midpoint(nodes[1][0],nodes[2][0],nodes[1][1],nodes[2][1],0)
		
		
		newnodes=[]
		newnodes.append(self.find_midpoint(nodes[0][0],nodes[15][0],nodes[0][1],nodes[15][1],9))
		newnodes.append(self.find_midpoint(nodes[16][0],nodes[17][0],nodes[16][1],nodes[17][1],10))
		newnodes.append(self.find_midpoint(nodes[1][0],nodes[12][0],nodes[1][1],nodes[12][1],11))
		newnodes.append(self.find_midpoint(center1[0],center2[0],center1[1],center2[1],12))
		newnodes.append(self.find_midpoint(nodes[2][0],nodes[7][0],nodes[2][1],nodes[7][1],13))
		newnodes.append(self.find_midpoint(nodes[20][0],nodes[21][0],nodes[20][1],nodes[21][1],14))
		newnodes.append(self.find_midpoint(nodes[3][0],nodes[4][0],nodes[3][1],nodes[4][1],15))
		newnodes.append(self.find_midpoint(nodes[18][0],nodes[19][0],nodes[18][1],nodes[19][1],16))
		newnodes.append(self.find_midpoint(nodes[9][0],nodes[10][0],nodes[9][1],nodes[10][1],17))
			
		
		heading_back=heading+180.0
		if heading_back>=360.0:
			heading_back=heading_back-360.0
		lat=newnodes[2][0]
		lon=newnodes[2][1]
		index=17
		xml.append('<parkingList>')
		yy=0
		for i in range(1,10):
			length_rad= self.park_spacing * i * METER_TO_NM * NM_TO_RAD
			lat2=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading))))
			lon2=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading))*math.sin(length_rad)/math.cos(math.radians(lat2))) + math.pi,2*math.pi)-math.pi)
			lat2_end=math.degrees(math.asin(math.sin(math.radians(lat))*math.cos(length_rad)+math.cos(math.radians(lat))*math.sin(length_rad)*math.cos(math.radians(heading_back))))
			lon2_end=math.degrees(math.fmod(math.radians(lon)-math.asin(math.sin(math.radians(heading_back))*math.sin(length_rad)/math.cos(math.radians(lat2_end))) + math.pi,2*math.pi)-math.pi)
			length_rad2=self.park_distance * METER_TO_NM * NM_TO_RAD
			heading2=heading+90
			
			if(heading2>=360):
				heading2=heading2-360
				
			heading2_back=heading2 +180
			if heading2_back >=360:
				heading2_back=heading2_back-360
				
			lat3=math.degrees(math.asin(math.sin(math.radians(lat2))*math.cos(length_rad2)+math.cos(math.radians(lat2))*math.sin(length_rad2)*math.cos(math.radians(heading2))))
			lon3=math.degrees(math.fmod(math.radians(lon2_end)-math.asin(math.sin(math.radians(heading2))*math.sin(length_rad2)/math.cos(math.radians(lat3))) + math.pi,2*math.pi)-math.pi)
			
			lat3_end=math.degrees(math.asin(math.sin(math.radians(lat2))*math.cos(length_rad2)+math.cos(math.radians(lat2))*math.sin(length_rad2)*math.cos(math.radians(heading2_back))))
			lon3_end=math.degrees(math.fmod(math.radians(lon2_end)-math.asin(math.sin(math.radians(heading2_back))*math.sin(length_rad2)/math.cos(math.radians(lat3_end))) + math.pi,2*math.pi)-math.pi)
			
			xml.append(self.gen_parking(lat3,lon3_end,yy,heading2_back))
			park.append((lat3,lon3,yy))
			index+=1
			subnodes.append((lat2,lon2_end,index))
			yy+=1
			
			
		xml.append('\n</parkingList>\n')
			
			
		xml.append('<TaxiNodes>\n')
		#print len(nodes)
		#print len(subnodes)
		#print len(park)
		
		
		
		for n in newnodes:
			coord=self.convert_coord(n[0],n[1])
			onrunway='0'
			hold='none'
			if n[2]==9 or n[2]==15 or n[2]==17:
				onrunway='1'
			if n[2]==10 or n[2]==14 or n[2]==16:
				hold='normal'
				
			xml.append('\t<node index="'+str(n[2])+'" lat="'+coord[0]+'" lon="'+coord[1]+'" isOnRunway="'+onrunway+'" holdPointType="'+hold+'" />\n')
			
			
		for n in subnodes:
			coord=self.convert_coord(n[0],n[1])
			xml.append('\t<node index="'+str(n[2])+'" lat="'+coord[0]+'" lon="'+coord[1]+'" isOnRunway="0" holdPointType="none" />\n')
			
		
		xml.append('</TaxiNodes>\n<TaxiWaySegments>\n')
		
		qq=0
		for p in park:
			xml.append('\t<arc begin="'+str(p[2])+'" end="'+str(subnodes[qq][2])+'" isPushBackRoute="0" name="" />\n')
			xml.append('\t<arc begin="'+str(subnodes[qq][2])+'" end="'+str(p[2])+'" isPushBackRoute="0" name="" />\n')
			qq+=1
		
		xml.append('\t<arc begin="'+str(newnodes[0][2])+'" end="'+str(newnodes[1][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[1][2])+'" end="'+str(newnodes[0][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(newnodes[1][2])+'" end="'+str(newnodes[2][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[2][2])+'" end="'+str(newnodes[1][2])+'" isPushBackRoute="0" name="" />\n')
				
		xml.append('\t<arc begin="'+str(newnodes[2][2])+'" end="'+str(subnodes[0][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(subnodes[0][2])+'" end="'+str(newnodes[2][2])+'" isPushBackRoute="0" name="" />\n')
		
		pp=0
		for s  in subnodes:
			if pp > len(subnodes)-2:
				break
			xml.append('\t<arc begin="'+str(s[2])+'" end="'+str(subnodes[pp+1][2])+'" isPushBackRoute="0" name="" />\n')
			xml.append('\t<arc begin="'+str(subnodes[pp+1][2])+'" end="'+str(s[2])+'" isPushBackRoute="0" name="" />\n')
			pp+=1
		
		
		
		xml.append('\t<arc begin="'+str(newnodes[3][2])+'" end="'+str(subnodes[-1][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(subnodes[-1][2])+'" end="'+str(newnodes[3][2])+'" isPushBackRoute="0" name="" />\n')
				
		xml.append('\t<arc begin="'+str(newnodes[3][2])+'" end="'+str(newnodes[4][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[4][2])+'" end="'+str(newnodes[3][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(newnodes[4][2])+'" end="'+str(newnodes[5][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[5][2])+'" end="'+str(newnodes[4][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(newnodes[6][2])+'" end="'+str(newnodes[5][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[5][2])+'" end="'+str(newnodes[6][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(newnodes[3][2])+'" end="'+str(newnodes[7][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[7][2])+'" end="'+str(newnodes[3][2])+'" isPushBackRoute="0" name="" />\n')
		
		xml.append('\t<arc begin="'+str(newnodes[7][2])+'" end="'+str(newnodes[8][2])+'" isPushBackRoute="0" name="" />\n')
		xml.append('\t<arc begin="'+str(newnodes[8][2])+'" end="'+str(newnodes[7][2])+'" isPushBackRoute="0" name="" />\n')
		

		
		xml.append('</TaxiWaySegments>\n</groundnet>\n')
		
		self.save_network(apt,xml,850)


	def save_network(self,apt,xml,version=810):
		buf="".join(xml)
		dir_path=''
		output_dir='output'
		if version==850:
			output_dir='output850'
		if self.save_tree==True:
			if len(apt)==4 or len(apt)==3:
				dir_path=os.path.join(os.getcwd(),output_dir,'Airports',apt[0],apt[1],apt[2])
			else:
				print "Airport ICAO has "+len(apt)+" letters, skipping"
				return
			if os.path.exists(dir_path)==False:
				try:
					os.makedirs(dir_path,0755)
				except:
					pass
		else:
			dir_path=os.path.join(os.getcwd(),output_dir)
		path=os.path.join(dir_path,apt+'.groundnet.xml')
		fw=open(path,'wb')
		fw.write(buf)
		fw.close()
		
	
	def find_midpoint(self,lat1,lat2,lon1,lon2,index):
		if lon1>lon2:
			lon=(lon1-lon2)/2 + lon2
		else:
			lon=(lon2-lon1)/2 + lon1
		if lat1>lat2:
			lat=(lat1-lat2)/2 + lat2
		else:
			lat=(lat2-lat1)/2 + lat1
		return (lat,lon,index)


	def gen_parking(self,lat,lon,index,heading):
		coord=self.convert_coord(lat,lon)
		buf='''
		<Parking index="'''+str(index)+'''"
			 type="gate"
			 name="Gate"
			 number="'''+str(index+1)+'''"
			 lat="'''+coord[0]+'''"
			 lon="'''+coord[1]+'''"
			 heading="'''+str(heading)+'''"
			 radius="28"
			 airlineCodes="" />'''
		return buf
				
			
	def convert_coord(self,lat,lon):
		coord=[]
		str_lat=''
		str_lon=''
		if lat>0:
			str_lat+='N'
		else:
			str_lat+='S'
		if lon>0:
			str_lon+='E'
		else:
			str_lon+='W'
		mod_lat=math.modf(lat)
		lat=int(math.fabs(mod_lat[1]))
		lat_deg=math.fabs(mod_lat[0]) *60
		str_lat+=str(lat)+' '+str(lat_deg)
		
		mod_lon=math.modf(lon)
		lon=int(math.fabs(mod_lon[1]))
		lon_deg=math.fabs(mod_lon[0]) *60
		str_lon+=str(lon)+' '+str(lon_deg)
		coord.append(str_lat)
		coord.append(str_lon)
		return coord
		


if __name__ == "__main__":
	if len(sys.argv) <2:
		print 'Usage: groundnet.py all | airport <ICAO> [850]'
		sys.exit()
	else:
		if sys.argv[1]=='airport':
			if len(sys.argv) <3:
				print 'Usage: groundnet.py airport <ICAO> [850]'
				sys.exit()
			elif len(sys.argv) == 4 and sys.argv[3]== '850':
				apt=sys.argv[2]
				parser=Groundnet(850)
				parser.parse_airport(apt)
			else:
				apt=sys.argv[2]
				parser=Groundnet()
				parser.parse_airport(apt)
		elif sys.argv[1]=='all':
			if len(sys.argv) == 3 and sys.argv[2]== '850':
				parser=Groundnet(850)
			else:
				parser=Groundnet()
			parser.parse_all()
		else:
			print 'Usage: groundnet.py all | airport <ICAO> [850]'
			sys.exit()
