#!/usr/bin/env python

"""
Usage: fanatic.py [options]

totally grab your fanatic badge

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -v, --verbose         display debugging output
  -f, --fake            fake a successful connect
  -r, --reset           reset the day count history
  -g, --growl           growl the successful connect
  -p, --prowl           prowl the successful connect
  -c CONFIG_FILE, --config=CONFIG_FILE
                        config file to use
"""

import sys

import time
import os.path
import urllib2
import pickle

from time import gmtime, strftime
from optparse import OptionParser

try:
    import ClientCookie
except ImportError:
    sys.stderr.write("Error: Required ClientCookie module not found.\n"
            "ClientCookie can be downloaded from:\n"
            "http://wwwsearch.sourceforge.net/ClientCookie/\n\n")
    sys.exit(1)

try:
    import yaml
except ImportError:
    sys.stderr.write("Error: Required PyYAML module not found.\n"
            "PyYAML can be downloaded from:\n"
            "http://www.pyyaml.org/\n\n")
    sys.exit(1)

DEFAULTS = {
    'verbose': 0,
    'reset' : 0,
    'fake' : 0,
    'growl' : 0,
    'prowl' : 0,
    'config' : 'fanatic.yml'
}

if not os.path.exists(DEFAULTS['config']):
    sys.stderr.write("Error: No config file found!\n")
    sys.exit(1)

# General configuration
URL = "http://www.stackoverflow.com/"
USER_AGENT = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_8; en-us) AppleWebKit/530.19.2 (KHTML, like Gecko) Version/4.0.2 Safari/530.19"
TOKEN_STRING = "gavin-gilmour" # Crude as hell token to determine if we are logged in or not
FANATIC_DAY_THRESHOLD = 100
MESSAGE_TITLE = "Stackoverflow hit!"
MESSAGE_BODY = "Only %d days to go! (you're on day %d ^_^)"

options = {}
config = yaml.load(file(DEFAULTS['config'], 'r'))

class Fanatic:

    def __init__(self):
        self.count = 0
        self.count_file = os.path.expanduser('~/.fanatic/count.pickle')
        self.name = self.__class__.__name__.lower()
        self._load()

    def debug(self, msg):
        if options['verbose']:
            self.output('[DEBUG]: ' + msg)

    def output(self, msg):
        print "[%s] %s" % (strftime("%m/%d/%y %H:%M:%S", gmtime()), msg)

    def _load(self):
        if os.path.exists(self.count_file) and not options['reset']:
            self.debug("Reading count..")
            self.count = pickle.load(open(self.count_file, 'rb'))

    def _save(self):
        self.debug("Updating count..")
        if not os.path.exists(os.path.expanduser('~/.fanatic/')):
            os.mkdir(os.path.expanduser('~/.fanatic/'))
        self.count = self.count + 1
        pickle.dump(self.count, open(self.count_file, 'wb'))
        self.debug("Done.")

    def fetch(self):
        self.debug("Fetching page")

        try:
            cj = ClientCookie.MozillaCookieJar()
            cj.load(config['config']['cookie_file'])
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders = [('User-agent', USER_AGENT)]
            self.debug(URL)
            try:
                # TODO: Some sort of random delay will be good here!
                if not options['fake']:
                    page = opener.open(URL)
                    logged_in = TOKEN_STRING in page.read()
                else:
                    self.debug("Faking a hit guys")
                    logged_in = True

                if not logged_in:
                    print "Error: Doesn't look like you've been logged in. Abort!"
                    sys.exit(0)

                # We made it! What day is it now?
                self._save()

                if options['prowl']:
                    self.do_prowl()

                if options['growl']:
                    self.do_growl()
            except urllib2.URLError, e:
                print "Error: %s" % e.reason
        except ClientCookie._ClientCookie.LoadError:
            print "Error: Cookie file looks malformed."
        except urllib2.HTTPError:
            print "Error: Couldn't reach the page. Check your credentials?"

    def do_prowl(self):
        try:
            import prowlpy
        except ImportError:
            print "Error: Couldn't load in prowlpy"
            return

        p = prowlpy.Prowl(config['config']['prowl_key'])
        try:
            body = MESSAGE_BODY % ((FANATIC_DAY_THRESHOLD - self.count), self.count)
            p.add(self.name, MESSAGE_TITLE, body)
        except Exception, e:
            print "Error: %s" % e

    def do_growl(self):
        try:
            import netgrowl
            from socket import AF_INET, SOCK_DGRAM, socket
        except ImportError:
            print "Error: Couldn't load in netgrowl"
            return

        addr = (config['config']['growl_host'], netgrowl.GROWL_UDP_PORT)
        s = socket(AF_INET,SOCK_DGRAM)
        p = netgrowl.GrowlRegistrationPacket(application=self.name)
        p.addNotification(self.name, enabled=True)
        s.sendto(p.payload(), addr)

        self.debug("Growling!")
        p = netgrowl.GrowlNotificationPacket(
                application=self.name,
                notification=self.name,
                title=MESSAGE_TITLE,
                description=MESSAGE_BODY % ((FANATIC_DAY_THRESHOLD - self.count), self.count)
            )
        s.sendto(p.payload(), addr)
        s.close()

def main():
    parser = OptionParser(usage="%prog [options]", version="0.1",
            description="totally grab your fanatic badge")
    parser.add_option('-v', '--verbose', dest='verbose',
            help='display debugging output', action="store_const", const=1)
    parser.add_option('-f', '--fake', dest='fake',
            help='fake a successful connect', action="store_const", const=1)
    parser.add_option('-r', '--reset', dest='reset',
            help='reset the day count history', action="store_const", const=1)
    parser.add_option('-g', '--growl', dest='growl',
            help='growl the successful connect', action="store_const", const=1)
    parser.add_option('-p', '--prowl', dest='prowl',
            help='prowl the successful connect', action="store_const", const=1)
    parser.add_option('-c', '--config', dest='config_file',
            help='config file to use', action="store")
    parser.set_defaults(**DEFAULTS)
    (option_obj, args) = parser.parse_args()

    options['verbose'] = option_obj.verbose
    options['config'] = option_obj.config_file
    options['reset'] = option_obj.reset
    options['fake'] = option_obj.fake
    options['growl'] = option_obj.growl
    options['prowl'] = option_obj.prowl

    if options['config']:
        if not os.path.exists(options['config']):
            parser.error("config file must actually exist ;-(")

    cookie_file = config['config']['cookie_file']
    if cookie_file and not os.path.exists(cookie_file):
        print "fanatic.py: error: could not open cookie file '%s'" % cookie_file
        sys.exit(1)

    fanatic = Fanatic()
    try:
        fanatic.fetch()
    except KeyboardInterrupt:
        print "Caught sigterm. Cleaning up.."

if __name__ == "__main__":
    main()
