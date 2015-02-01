#!/usr/bin/env python

import email.charset
import email.message
import email.utils
import os
import pwd
import shlex
import smtplib
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

	with open(template_file, 'r') as f:
		template = f.read()

	print('* Fetching repositories.xml ...')
	with urllib_req.urlopen('https://api.gentoo.org/overlays/repositories.xml') as f:
		repos_xml = ET.parse(f)

	print('* Connecting to SMTP ...')
	try:
		smtp_config = conf['smtp']
	except KeyError:
		smtp_config = {}

	if smtp_config.get('ssl'):
		smtp_class = smtplib.SMTP_SSL
	else:
		smtp_class = smtplib.SMTP

	with smtp_class(smtp_config.get('host', '')) as smtp:
		if smtp_config.get('tls'):
			smtp.starttls()
		smtp.ehlo()
		if smtp_config.get('username') and smtp_config.get('password'):
			smtp.login(smtp_config['username'], smtp_config['password'])

		try:
			mail_from = conf['user']['email']
		except KeyError:
			if smtp_config.get('username'):
				mail_from = smtp_config.get('username')
			else:
				mail_from = pwd.getpwuid(os.getuid()).pw_name
			if smtp_config.get('host'):
				mail_from += '@' + smtp_config['host']

		print('* Processing input ...')
		with open(data_file, 'r') as f:
			for l in f:
				l = shlex.split(l)
				if l:
					repo_name = l[0]
					print('%s' % repo_name)
					repo = repos_xml.find('./repo[name="%s"]' % repo_name)
					assert(repo)

					mail_to = []
					for o in repo.findall('owner'):
						mail = o.find('email')
						assert(mail is not None)

						name = o.find('name')
						mail_to.append((name.text if name is not None else None,
							mail.text))
					assert(mail_to)
					mail_to.append(('Gentoo Overlays', 'overlays@gentoo.org'))

					mail_body = template
					for i, lf in enumerate(l):
						tag = '${%d}' % (i+1)
						mail_body = mail_body.replace(tag, lf)
				
					mail_body = mail_body.replace('${fullname}', fullname)

					mail_subj, mail_body = mail_body.split('\n\n', 1)
					mail_body = '\n'.join(textwrap.fill(x, 72)
							for x in mail_body.split('\n'))

					# get some sanity into Python...
					charset = email.charset.Charset('utf-8')
					charset.header_encoding = email.charset.QP
					charset.body_encoding = email.charset.QP

					msg = email.message.Message()
					msg.set_charset(charset)
					msg.set_payload(charset.body_encode(mail_body))
					msg['From'] = email.utils.formataddr(
							('%s (on behalf of Gentoo Overlays Project)' % fullname,
								mail_from))
					msg['To'] = email.utils.formataddr(mail_to[0])
					if len(mail_to) > 1:
						msg['CC'] = ', '.join(email.utils.formataddr(x) for x in mail_to[1:])
					msg['Subject'] = mail_subj
					msg['Date'] = email.utils.formatdate()
					msg['Message-Id'] = email.utils.make_msgid()

					smtp.sendmail(mail_from, [x[1] for x in mail_to], msg.as_string())

	print('Done.')


if __name__ == '__main__':
	main(*sys.argv[1:])
