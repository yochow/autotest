import sys, string, os

def check_python_version():
	version = None
	try:
		version = sys.version_info[0:2]
	except AttributeError:
		pass # pre 2.0, no neat way to get the exact number
	if not version or version < (2, 4):
                for new in ('/usr/bin/python2.4', '/usr/local/bin/python2.4'):
                        if os.path.exists(new):
                                sys.argv.insert(0, '-u')
                                sys.argv.insert(0, new)
                                os.execv(sys.argv[0], sys.argv)
		raise ValueError('Python 2.4 or newer is needed')