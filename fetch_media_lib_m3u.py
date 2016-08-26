#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import sys
import urllib2
import os
import signal
import time
import re
import shutil
import argparse

subURL='m/'
mpg123='mpg123'
playListDir='./'
baseDir='/usr/local/www/snd/'
diskSizeLimit=1024^3
terminate = False

def signal_handling(signum,frame):
	global terminate
	terminate = True
	print >>sys.stderr, 'Signal catched'

def SplitURL(url):
	pos=url.rfind('/')+1
	if pos > 0:
		fname=url[pos:]
		hname=url[:pos]
	else:
		fname=url[pos:]
		hname=''
	return([hname,fname])

def playMP3(url):
	cmdString=mpg123+' -q "'+url+'"'
	os.system(cmdString)
#	try:
#		retcode = subprocess.call(cmdString, shell=True)
#		if retcode < 0:
#			print >>sys.stderr, 'Child was terminated by signal', -retcode
#		else:
#			print >>sys.stderr, 'Child returned', retcode
#	except OSError as e:
#		print >>sys.stderr, 'Execution failed:', e

def getPlaylistFromURL(url):
	req = urllib2.Request(url)
	try:
		response=urllib2.urlopen(req)
		s=response.read()
		return(s)
	except urllib2.URLError as e:
		sys.stderr.write('URL '+url+' not fetched: '+e.reason+'\n')
		exit(1)

def getPlaylistFromFile(f):
	try:
		infile=open(f);
		s=infile.read()
		infile.close()
		return(s)
	except IOError as e:
		sys.stderr.write('Can\'t read from file '+f+': '+e.strerror+'\n')
		exit(1)

def httpFetch(url,target):
	mp3file = urllib2.urlopen(url)
	output = open(target,'wb')
	meta = mp3file.info()
	file_size = int(meta.getheaders("Content-Length")[0])
	print >>sys.stderr,"Downloading: %s to %s size: %s" % (url, target, file_size)

#	file_size_dl = 0
#	block_sz = 8192
#	while True:
#		buffer = mp3file.read(block_sz)
#		if not buffer:
#			break
#
#		file_size_dl += len(buffer)
#		output.write(buffer)
#		status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
#		status = status + chr(8)*(len(status)+1)
#		print status,

	output.write(mp3file.read())
	output.close()
	return

def fileCopy(source,target):
	if os.path.islink(source):
		realSrc=os.readlink(source)
	else:
		realSrc=source
	print >>sys.stderr,"Copy: %s to %s" % (realSrc,target)
	shutil.copyfile(realSrc,target)
	return

def getFreeSize(path):
	st = os.statvfs(path)
	return(st.f_bavail * st.f_frsize)

def countSizeLimit(sizeLimit,destDir):
	diskSizeLimit=int(getFreeSize(destDir) * 0.9 + 0.5)
	if sizeLimit != '0':
		sizeLimit=sizeLimit.lower()
		p=re.match('^\d+$',sizeLimit)
		if (p):
			diskSizeLimit=int(sizeLimit)
		else:
			p=re.match('^(\d+)([gmkb\%])$',sizeLimit)
			if (p):
				if p.group(2) == 'b':
					diskSizeLimit=int(p.group(1))
				elif p.group(2) == 'k':
					diskSizeLimit=int(p.group(1))*1024
				elif p.group(2) == 'm':
					diskSizeLimit=int(p.group(1))*1024**2
				elif p.group(2) == 'g':
					diskSizeLimit=int(p.group(1))*1024**3
				elif p.group(2) == '%':
					i=int(p.group(1))
					if i > 0 and i < 101:
						diskSizeLimit=int(getFreeSize(destDir) / 100 * i + 0.5)
	return diskSizeLimit

parser = argparse.ArgumentParser(description='Fetch medialibrary data')
parser.add_argument('--play', action='store_true', default=False, help='play mode')
parser.add_argument('--sync', action='store_true', default=False, help='sync mode')
parser.add_argument('--save', default='',help='save transition playlist to file')
parser.add_argument('--file', default='',help='playlist file ( without extension )')
parser.add_argument('--url', default='',help='url of playlist ( without extension )')
parser.add_argument('--limit', default='0',help='free size limit')
parser.add_argument('--destination', default='',help='destination folder')
cmdarg=parser.parse_args()

if len(cmdarg.file) > 0 and len(cmdarg.url) > 0 :
	sys.stderr.write('Too many sources, only one allowed\n')
	exit(1)

if cmdarg.play and cmdarg.sync :
	sys.stderr.write('Too many actions, only one allowed\n')
	exit(1)

data=''
aout=[]
descrs={}
extinf={}
descr=''
fulldescr=''
location={}
httpMode=False
saveFile=False

if len(cmdarg.url) > 0:
	[basePath,playLstName]=SplitURL(cmdarg.url)
	if len(playLstName) == 0:
		sys.stderr.write('Playlist not set\n')
		exit(1)
	data=getPlaylistFromURL(cmdarg.url)
	httpMode=True
elif len(cmdarg.file) > 0:
	data=getPlaylistFromFile(cmdarg.file)
	basePath=baseDir
else:
	sys.stderr.write('Source not set\n')
	exit(1)

if len(data) == 0:
	sys.stderr.write('Empty playlist\n')
	exit(1)

if len(cmdarg.save) > 0:
	saveFile=True

for stri in data.split('\n'):
	if stri.find('#EXTM3U') > -1:
		continue
	elif stri.find('#EXTINF:') > -1:
		Comma=stri.find(',')
		if Comma > -1:
			descr=stri[Comma+1:-5]
		if saveFile:
			fulldescr=stri
	elif len(stri) > 0:
		aout.append(stri)
		location[stri]=basePath+subURL+stri
		descrs[stri]=descr
		descr=''
		if saveFile:
			extinf[stri]=fulldescr
			fulldescr=''

if len(aout) < 1:
	sys.stderr.write('Empty playlist\n')
	exit(1)

if saveFile:
	try:
		f=open(cmdarg.save, 'w')
		bout='#EXTM3U\n'
		for stri in aout:
			bout+=extinf[stri]+'\n'+location[stri]+'\n'
		f.write(bout)
		f.close
		bout=''
	except IOError as e:
		sys.stderr.write('Can\'t write to file '+cmdarg.save+': '+e.strerror+'\n')
		exit(1)

if cmdarg.play:
	signal.signal(signal.SIGINT,signal_handling)
	for stri in aout:
		if len(descrs[stri]) > 0:
			print '\nNow playing:',descrs[stri],'\n'
		playMP3(location[stri])
		time.sleep(.3)
		if terminate:
			break
	exit()

if not cmdarg.sync:
	sys.stderr.write('Actions not set, run sync\n')
if len(cmdarg.destination) == 0 :
	sys.stderr.write('Not set destination directory for sync\n')
	exit(1)
if not os.path.exists(cmdarg.destination):
	sys.stderr.write('Directory '+cmdarg.destination+' not exists\n')
	exit(1)
diskSizeLimit=countSizeLimit(cmdarg.limit,cmdarg.destination)
localDirLst=os.listdir(cmdarg.destination)

for mFile in localDirLst:
	if not mFile in location:
		os.remove(os.path.normpath(os.path.join(cmdarg.destination,mFile)))
		sys.stderr.write('File '+mFile+' deleted\n')

for mFile in aout:
	mFileAbs=os.path.normpath(os.path.join(cmdarg.destination,mFile))
	if not os.path.exists(mFileAbs):
		if httpMode:
			httpFetch(location[mFile],mFileAbs)
		else:
			fileCopy(location[mFile],mFileAbs)
		freeSize=getFreeSize(cmdarg.destination)
		sys.stderr.write('Free size ' + str(freeSize) + '\n')
		if freeSize <= diskSizeLimit:
			sys.stderr.write('Limit of disk usage reached\n')
			exit(1)
