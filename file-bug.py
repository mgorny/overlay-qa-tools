#!/usr/bin/env python
# (c) 2015 Michał Górny, 2-clause BSD licensed

from __future__ import print_function

import bugz.bugzilla
import os
import pwd
import shlex
import sys
import textwrap

try:
	import urllib.request as urllib_req
except ImportError:
	# Python 2
	import urllib as urllib_req
try:
	import configparser
except ImportError:
	import ConfigParser as configparser

import xml.etree.ElementTree as ET


def main(data_file, template_file):
	conf = configparser.ConfigParser()
	conf.read(['qatools.conf'])

	try:
		fullname = conf['user']['fullname']
	except KeyError:
		u = pwd.getpwuid(os.getuid())
		gecos = u.pw_gecos.split(',')
		fullname = gecos[0]

	token_file = os.path.expanduser('~/.bugz_token')
	try:
		with open(token_file, 'r') as f:
			token = f.read().strip()
	except IOError:
		print('! Bugz token not found, please run "bugz login" first')
		return 1

	bz = bugz.bugzilla.BugzillaProxy('https://bugs.gentoo.org/xmlrpc.cgi')

	with open(template_file, 'r') as f:
		template = f.read()

	print('* Fetching repositories.xml ...')
	with urllib_req.urlopen('https://api.gentoo.org/overlays/repositories.xml') as f:
		repos_xml = ET.parse(f)

	print('* Processing input ...')
	with open(data_file, 'r') as f:
		for l in f:
			l = shlex.split(l)
			if l:
				repo_name = l[0]
				print('%s' % repo_name, end='', flush=True)
				try:
					repo = repos_xml.find('./repo[name="%s"]' % repo_name)
					if not repo:
						print('!! repo %s does not exist!' % repo_name)
						continue

					mail_to = []
					for o in repo.findall('owner'):
						mail = o.find('email')
						assert(mail is not None)
						mail_to.append(mail.text)
					assert(mail_to)
					mail_to.append('overlays@gentoo.org')

					mail_body = template
					for i, lf in enumerate(l):
						tag = '${%d}' % (i+1)
						mail_body = mail_body.replace(tag, lf)
				
					mail_body = mail_body.replace('${fullname}', fullname)

					mail_subj, mail_body = mail_body.split('\n\n', 1)
					mail_body = '\n'.join(textwrap.fill(x, 72)
							for x in mail_body.split('\n'))

					params = {
						'Bugzilla_token': token,
						'product': 'Gentoo Infrastructure',
						'component': 'Gentoo Overlays',
						'version': 'unspecified',
						'summary': mail_subj,
						'description': mail_body,
						'assigned_to': mail_to[0],
						'cc': ', '.join(mail_to[1:]),
					}

					ret = bz.Bug.create(params)
				except Exception as e:
					print('') # newline ;)
					raise
				else:
					print(' -> %d' % ret['id'])

	print('Done.')


if __name__ == '__main__':
	main(*sys.argv[1:])
