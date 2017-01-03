#!/usr/bin/env python

import os, sys, re, platform
import subprocess
import ConfigParser
import collections
from optparse import OptionParser

HANDLE_DUPS = True

PKG_NOT_INSTALLED=0
PKG_INSTALLED=0x1
PKG_HOLD=0x2


class MultiDict(dict):
    def __setitem__(self, key, value):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            super(self.__class__, self).__setitem__(key, value)


class PackageInfo(object):
    '''Information describing a package'''
    def __init__(self, name=None, state=0, version=None, requiredVersion=None, candidateVersion=None, arch=None):
        self._name = name
        self._state = state
        self._version = version
        self._required_version = requiredVersion
        self._arch = arch
        self._custom_action = None
        self._candidate_version = candidateVersion

    def isInstalled(self):
        return 0 != (self._state & PKG_INSTALLED)

    def isOnHold(self):
        return 0 != (self._state & PKG_INSTALLED) and 0 != (self._state & PKG_HOLD)

    def getName(self):
        return self._name

    def getVersion(self, raw=False):
        if raw:
            return self._version or 'none'
        return self._version or 'latest'

    def getRequiredVersion(self, raw=False):
        if raw:
            return self._required_version or 'none'
        return self._required_version or 'latest'

    def getCandidateVersion(self, raw=False):
        if raw:
            return self._candidate_version or 'none'
        if self.getRequiredVersion() == 'latest':
            return 'latest'
        return self._candidate_version or 'latest'

    def getCustomAction(self):
        return self._custom_action


allPackageMgrs = {}


class PackageMgr(object):
    '''Generic package manager class
    '''
    def __init__(self, name=None, noroot=False):
        self._name = name
        self._noroot = noroot

    @classmethod
    def addPackageMgr(cls):
        allPackageMgrs[cls.__name__] = cls

    @staticmethod
    def getPackageMgr(name):
        return allPackageMgrs.get(name)

    def getName(self):
        return self._name

    def getPackageInfo(self, names, debug=True):
        '''Get installed list of PackageInfo instances

        Override this in derived classes.
        '''
        raise NotImplemented()

    def installPackages(self, packageList, update, debug, verbose):
        '''Install packages.
        Override this in derived classes.

        Args:
            packageList: list of PackageInfo instances
            update: boolean indicating if an update of available packages is
                required.
            debug: If true commands are sent to stdout but not executed.
        '''
        raise NotImplemented()

    def refreshPackageCandidates(self, packageList, debug):
        '''Refresh candidate version..
        Override this in derived classes.

        Args:
            packageList: list of PackageInfo instances
            debug: If true commands are sent to stdout but not executed.
        '''
        raise NotImplemented()

    def execute(self, command, debug, verbose=False):
        if debug:
            print(command)
            return True
        else:
            if verbose:
                print(command)
            return 0 == os.system(command)

    def executeAsRoot(self, command, debug, verbose=False):
        if not self._noroot and os.getuid() != 0:
            command = 'sudo ' + command;
        return self.execute(command, debug=debug, verbose=verbose)

    def checkVersionLess(self, ver1, ver2):
        '''Check if ver1 < ver2
        '''
        ver1 = ver1.replace('-','.').split('.')
        ver2 = ver2.replace('-','.').split('.')
        for i in range(min(len(ver1),len(ver2))):
            v1 = int(ver1[i])
            v2 = int(ver2[i])
            if v1 < v2:
                return True
            elif v1 > v2:
                return False
        # must be equal so far
        return len(ver1) < len(ver2)

    def prepareInstall(self, pkgs):
        # Prepare package install into to lists
        to_install = []
        needs_update = []
        for p in pkgs:
            if not p.isInstalled():
                if p.getRequiredVersion() == 'latest':
                    to_install.append(p)
                elif p.getCandidateVersion() != 'latest' and \
                    self.checkVersionLess(p.getRequiredVersion(), p.getCandidateVersion()):
                    to_install.append(p)
                else:
                    needs_update.append(p)
            elif p.isOnHold():
                warning('%s is on hold, ignoring install request' % p.getName())
            elif p.isInstalled() and p.getRequiredVersion() != 'latest' \
                and self.checkVersionLess(p.getVersion(),p.getRequiredVersion()):
                needs_update.append(p)
        return (to_install, needs_update)


class AptPackageMgr(PackageMgr):
    '''Apt'''
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._threshold = 500 # just a guess
        # dpkg-query sample output
        # un  www-browser
        # ii  x11-common 1:7.7+1ubuntu8.1
        # ii  x11proto-composite-dev 1:0.4.2-2
        # ii  x11proto-core-dev 7.0.26-1~ubuntu2
        # ii  x11proto-xinerama-dev 1.2.1-2
        # ii  xauth 1:1.0.7-1ubuntu1
        # ii  xfonts-encodings 1:1.0.4-1ubuntu1
        # ii  xfonts-utils 1:7.7+1
        # ii  cmake 3.2.2-2~ubuntu14.04.1~ppa1
        self._dpkg_query = re.compile(r'^([a-zA-Z ]{3})\s([+.\w_-]+)(?::\w+)?\s(?:\d+:)?(\d[.\d-]*\d)[~+.\w_-]*\s*$')
        # apt-cache policy git sample output
        # git:
        #   Installed: 1:1.9.1-1ubuntu0.3
        #   Candidate: 1:1.9.1-1ubuntu0.3
        #   Version table:
        #      1:1.9.1-1ubuntu0.3 0
        #         500 http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ trusty-updates/main amd64 Packages
        #         500 http://security.ubuntu.com/ubuntu/ trusty-security/main amd64 Packages
        #  *** 1:1.9.1-1ubuntu0.3 0
        #         100 /var/lib/dpkg/status
        #      1:1.9.1-1 0
        #         500 http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ trusty/main amd64 Packages
        # cmake:
        #   Installed: 3.2.2-2~ubuntu14.04.1~ppa1
        #   Candidate: 3.2.2-2~ubuntu14.04.1~ppa1
        #   Version table:
        #  *** 3.2.2-2~ubuntu14.04.1~ppa1 0
        #         500 http://ppa.launchpad.net/george-edison55/cmake-3.x/ubuntu/ trusty/main amd64 Packages
        #         100 /var/lib/dpkg/status
        #      2.8.12.2-0ubuntu3 0
        #         500 http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ trusty/main amd64 Packages
        #self._apt_query = re.compile(r'^\s*installed:(?:\d+:)?(?P<installed>\d[.\d-]*\d)[~+.\w_-]*\s*$|^\s*candidate:(?:\d+:)?(?P<candidate>\d[.\d-]*\d)[~+.\w_-]*\s*$', \
        self._apt_query = re.compile(r'^\s*installed:\s*(?:\d+:)?(?P<installed>\d[.\d-]*\d)\D.*$|^\s*candidate:\s*(?:\d+:)?(?P<candidate>\d[.\d-]*\d)\D.*$', \
                        flags=re.MULTILINE|re.IGNORECASE)

    def _parseDpkgQuery(self, result):
        # ii  zlib1g-dev:amd64 1:1.2.8.dfsg-1ubuntu1
        srch = self._dpkg_query.match(result)
        if srch is not None:
            #print("DEBUG " + str((srch.group(0),srch.group(1),srch.group(2),srch.group(3))))
            pkg = PackageInfo(name=srch.group(2), version=srch.group(3))
            if srch.group(1)[0] in 'i':
                pkg._state = PKG_INSTALLED
            elif srch.group(1)[0] == 'h':
                pkg._state = PKG_INSTALLED|PKG_HOLD
            return pkg
        return None

    def _queryApt(self, pkgname, FNULL=None, debug=False):
        if debug:
            print('  Running apt-cache policy %s' % pkgname);
        if FNULL is None:
            with open(os.devnull, 'w') as FNULL:
                result = subprocess.Popen(['apt-cache', 'policy', pkgname], \
                        stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
        else:
            result = subprocess.Popen(['apt-cache', 'policy', pkgname], \
                    stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
        srch = self._apt_query.search(result)
        if srch is not None:
            candidate = None
            installed = None
            if srch.group('installed') is not None and len(srch.group('installed')):
                installed = srch.group('installed')
            if srch.group('candidate') is not None and len(srch.group('candidate')) != 0:
                candidate = srch.group('candidate')
            if debug:
                if installed is None and candidate is None:
                    print('    result inconclusive')
                    print('--------------')
                    print(result)
                    print('--------------')
                else:
                    print('    result = (%r,%r)' % (installed, candidate))
            return (installed, candidate)
        elif debug:
            print('    no results')
            print('--------------')
            print(result)
            print('--------------')
        return (None,None)

    def installPackages(self, packageList, update=False, debug=False, verbose=False):
        '''Install packages.

        Args:
            packageList: list of PackageInfo instances
            update: if True then an update of available packages is required
                before install.
            debug: If true commands are sent to stdout but not executed.
        '''
        if self._noroot or os.getuid() == 0:
            updatefmt = 'aptitude %s'
            installfmt = 'aptitude -y install %s'
        else:
            updatefmt = 'sudo aptitude %s'
            installfmt = 'sudo aptitude -y install %s'

        if update:
            self.execute(updatefmt % 'update', debug=debug, verbose=verbose)
            self.execute(updatefmt % '-y upgrade', debug=debug, verbose=verbose)

        args = ''
        for pkg in packageList:
            if (len(pkg.getName()) + 1 + len(args)) > 80:
                self.execute(installfmt % args, debug=debug, verbose=verbose)
                args = ''
            args += ' ' + pkg.getName()
        if len(args) != 0:
            self.execute(installfmt % args, debug=debug, verbose=verbose)

    def refreshPackageCandidates(self, packageList, debug=False):
        '''Refresh candidate version..

        Args:
            packageList: list of PackageInfo instances
            debug: If true commands are sent to stdout but not executed.
        '''
        with open(os.devnull, 'w') as FNULL:
            for pkg in packageList:
                pkg._version,pkg._candidate_version = self._queryApt(pkg.getName(), FNULL, debug=debug)

    def getPackageInfo(self, names, debug=True):
        '''Get packages in same order a names

        Args:
            names: list of package names.
            debug: If true commands are sent to stdout but not executed.

        Returns:
            A tuple (list of PackageInfo instances, list of missing names).
        '''
        if not isinstance(names, collections.Iterable):
            names = { names: 'latest' }
        pkgs = []
        missing = []
        if len(names) > self._threshold and not debug:
            # At some threshold its cheaper to get all packages installed.
            allpkgs = {}
            with open(os.devnull, 'w') as FNULL:
                results = subprocess.Popen(['dpkg-query', '-f=${db:Status-Abbrev} ${binary:Package} ${Version}\n', '-W', '*'], \
                        stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
            results = results.split('\n')
            for result in results:
                if len(result) == 0:
                    continue
                pkg = self._parseDpkgQuery(result)
                if pkg is not None:
                    allpkgs[pkg.getName()] = pkg
            for nm in names:
                pkg = allpkgs.get(nm[0])
                if pkg is not None:
                    pkg._required_version = nm[1]
                    if len(nm) == 3:
                        pkg._custom_action = nm[2]
                    if pkg.getRequiredVersion() != 'latest':
                        # Check using apt-cache
                        _,pkg._candidate_version = self._queryApt(nm[0], debug=debug)
                    pkgs.append(pkg)
                else:
                    # Check using apt-cache
                    installed, candidate = self._queryApt(nm[0], debug=debug)
                    if installed is not None:
                        warning('dpkg-query parse failure - check regex in this script')
                        pkg = PackageInfo(name=nm[0],state=PKG_INSTALLED,version=installed,requiredVersion=nm[1],candidateVersion=candidate)
                        pkgs.append(pkg)
                    elif candidate is not None:
                        pkg = PackageInfo(name=nm[0],version=installed,requiredVersion=nm[1],candidateVersion=candidate)
                        pkgs.append(pkg)
                    else:
                        # will need to do apt-get update
                        missing.append(nm)
        else:
            for nm in names:
                with open(os.devnull, 'w') as FNULL:
                    result = subprocess.Popen(['dpkg-query', '-f=${db:Status-Abbrev} ${binary:Package} ${Version}\n', '-W', nm[0]], \
                            stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
                result = result.strip('\n')
                if debug:
                    print('dpkg-query %s result=%s' % (nm[0], result))
                pkg = self._parseDpkgQuery(result)
                if pkg is not None:
                    pkg._required_version = nm[1]
                    if len(nm) == 3:
                        pkg._custom_action = nm[2]
                    if pkg.getRequiredVersion() != 'latest':
                        # Check using apt-cache
                        _,pkg._candidate_version = self._queryApt(nm[0], debug=debug)
                    pkgs.append(pkg)
                else:
                    # Check using apt-cache
                    installed, candidate = self._queryApt(nm[0], debug=debug)
                    if installed is not None:
                        warning('dpkg-query parse failure - check regex in this script')
                        pkg = PackageInfo(name=nm[0],state=PKG_INSTALLED,version=installed,requiredVersion=nm[1],candidateVersion=candidate)
                        pkgs.append(pkg)
                    elif candidate is not None:
                        pkg = PackageInfo(name=nm[0],version=installed,requiredVersion=nm[1],candidateVersion=candidate)
                        pkgs.append(pkg)
                    else:
                        # will need to do apt-get update
                        missing.append(nm)

        return (pkgs, missing)


class PipPackageMgr(PackageMgr):
    '''Pip'''
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        # scikit-image (0.12.3)
        # scikit-learn (0.17.1)
        # scipy (0.17.1)
        self._pip_list = re.compile(r'(?P<pkgname>[\w.~-]+)\s*\((?P<installed>\d+[.\d-]*)\)')
        self._pip_search1 = re.compile(r'^(?P<pkgname>[\w.~-]+)\s*\((?P<candidate>\d+[.\d-]*)\)')
        self._pip_search2 = re.compile(r'^\s*INSTALLED:\s*(?P<installed>\d+[.\d-]*)')

    def _parsePipSearch1(self, result):
        srch = self._pip_search1.search(result)
        if srch is not None:
            pkg = PackageInfo(name=srch.group('pkgname'), candidateVersion=srch.group('candidate'))
            return pkg
        return None

    def _parsePipSearch2(self, pkg, result):
        srch = self._pip_search2.search(result)
        if srch is not None:
            pkg._version = srch.group('installed')
            return True
        return False

    def _parsePipList(self, result):
        srch = self._pip_list.search(result)
        if srch is not None:
            pkg = PackageInfo(name=srch.group('pkgname'), version=srch.group('installed'))
            pkg._state = PKG_INSTALLED
            return pkg
        return None

    def getPackageInfo(self, names, debug=True):
        '''Get packages in same order a names

        Args:
            names: list of package names.
            debug: If true commands are sent to stdout but not executed.

        Returns:
            A tuple (list of PackageInfo instances, list of missing names).
        '''
        if not isinstance(names, collections.Iterable):
            names = { names: 'latest' }
        pkgs = []
        missing = []
        allpkgs = {}
        with open(os.devnull, 'w') as FNULL:
            results = subprocess.Popen(['pip', 'list'], stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
        results = results.split('\n')
        for result in results:
            if len(result) == 0:
                continue
            pkg = self._parsePipList(result)
            if pkg is not None:
                allpkgs[pkg.getName()] = pkg
        todo = []
        for nm in names:
            pkg = allpkgs.get(nm[0])
            if pkg is not None:
                pkg._required_version = nm[1]
                if len(nm) == 3:
                    pkg._custom_action = nm[2]
                pkgs.append(pkg)
            else:
                todo.append(nm)

        with open(os.devnull, 'w') as FNULL:
            for nm in todo:
                pkg = None
                # Handle pips woeful search facilty inherited from pypi.
                target = re.split('[\d,.~-]', nm[0])
                results = subprocess.Popen(['pip', 'search', target[0]], stderr=FNULL, stdout=subprocess.PIPE).communicate()[0]
                if debug:
                    print('Searching for %s' % nm[0])
                    print('---------')
                    print(results)
                    print('---------')
                results = results.split('\n')
                for r in results:
                    if pkg is not None:
                        self._parsePipSearch2(pkg, r)
                        break
                    if r.find(nm[0]) == 0:
                        if debug: print('found partial match: %s' % r)
                        pkg = self._parsePipSearch1(r)
                        if pkg is not None and pkg.getName() != nm[0]:
                            pkg = None
                            continue
                        elif pkg is not None:
                            pkgs.append(pkg)
                if pkg is None:
                    missing.append(nm)
        return (pkgs, missing)

    def installPackages(self, packageList, update, debug, verbose):
        '''Install packages.

        Args:
            packageList: list of PackageInfo instances
            update: Ignored for PIP.
            debug: If true commands are sent to stdout but not executed.
        '''
        for pkg in packageList:
            if pkg.getRequiredVersion() != 'latest':
                self.executeAsRoot('pip install %s==%s' (pkg.getName(), pkg.getRequiredVersion()), debug=debug, verbose=verbose)
            else:
                self.executeAsRoot('pip install ' + pkg.getName(), debug=debug, verbose=verbose)

    def refreshPackageCandidates(self, packageList, debug):
        '''Refresh candidate version..
        Does nothing for PIP.

        Args:
            packageList: list of PackageInfo instances
            debug: If true commands are sent to stdout but not executed.
        '''
        pass


def die(msg=None):
    if msg is not None:
        print("Error: %s" % msg)
    sys.exit(1)


def warning(msg):
    print("Warning: %s" % msg)


def prepCustomAction(items):
    m = {}
    for k,v in items:
        m[k] = v
    if m.get('run') is None:
        return None
    if m.get('version') is None:
        m['version'] = 'latest'
    return m


def extractPackageNames(pkgs):
    '''Extract package names from a list of PackageInfo instances.

    Args:
        pkgs: A list of PackageInfo instances.

    Returns:
        A list of packages names
    '''
    if not isinstance(pkgs, collections.Iterable):
        pkgs = [ pkgs ]
    names = []
    for p in pkgs:
        names.append(p.getName())


def grep_platform(regex):
    try:
        regex = regex.split('/')
        if len(regex) == 3 and len(regex[0]) == 0:
            flags = 0
            if 'i' in regex[2]:
                flags |= re.IGNORECASE
            return re.search(regex[1], platform.platform(), flags=flags)
    except:
        pass
    die('bad regex %s in package-selector section' % regex)
    return False


def printPackageInfo(packages):
    for u in packages:
        #     0         1         2         3         4         5         6
        #     0123456789012345678901234567890123456789012345678901234567890
        print('  Package Name     Installed      Required     Candidate')
        print('  ------------     ---------      --------     ---------')
        print('  %-16s %-14s %-12s %-14s' % (u.getName(), u.getVersion(True), u.getRequiredVersion(True), u.getCandidateVersion(True)))


if __name__ == '__main__':
    print('Package Dependency Helper V0.1')

    # Parse command line
    usage = '%prog [[options] [file1.conf ...]]'
    parser = OptionParser(usage)
    parser.add_option('-l', '--list', action='store_true', dest='pkglist', help='list selected packages on stdout')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose output')
    parser.add_option('-i', '--install', action='store_true', dest='pkginstall', help='install selected packages')
    parser.add_option('-r', '--noroot', action='store_true', dest='noroot', help='do not install as root')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='used with install, print commands but don\'t execute')
    (options, args) = parser.parse_args()
    if args is None or len(args) == 0:
        die('no confguration file so nothing to do')

    # FIXME: custom action paths should be relative to the conf file
    # At the moment they are relative to the first conf file
    if len(args) > 1:
        warning("Custom actions are relative the first configuration file path.")
    base_path = os.path.abspath(os.path.dirname(args[0]))

    # Add supported package managers
    AptPackageMgr.addPackageMgr()
    PipPackageMgr.addPackageMgr()

    # Parse configuration files
    if HANDLE_DUPS:
        cfg = ConfigParser.ConfigParser(dict_type=MultiDict)
    else:
        cfg = ConfigParser.ConfigParser(dict_type=dict)
    cfg.optionxform = str # preserve case on keys
    success = cfg.read(args)
    mgrs = {}
    if not cfg.has_section('package-managers'):
        die('no package-managers in configuration file(s)')

    mgrMap = {}
    items = cfg.items('package-managers')
    for k,v in items:
        cls = PackageMgr.getPackageMgr(v)
        if cls is None:
            warning('%s package-manager class not found' % v)
            continue
        mgrMap[k] = cls(name=k, noroot=options.noroot)
    if len(mgrMap) == 0:
        die('no package-managers map to classes')

    # Disabled.
    #
    # Map package manager to platform
    # if not cfg.has_section('package-selector'):
    #    die('no package-selector in configuration file(s)')

    if cfg.has_section('package-selector'):
        # Remove package-managers not related to this platform
        mgr = None
        items = cfg.items('package-selector')
        for k,v in items:
            if mgrMap.get(k) is None:
                # No package-manager for this key so remove sections
                cfg.remove_section(k)
            elif not grep_platform(v):
                # This platform is not being used so remove from map and remove sections
                # in configuration
                mgrMap.pop(k)
                cfg.remove_section(k)
        if len(mgrMap) == 0:
            die('no package-managers after processing package-selector section')

    # Load packages for each package-manager
    selections = []
    for k,mgr in mgrMap.iteritems():
        if not cfg.has_section(k):
            continue

        items = cfg.items(k)
        # Check duplicates
        if HANDLE_DUPS:
            for T in items:
                tmp = T[1].split('\n')
                if len(tmp) > 1:
                    die('requested multiple versions for package %s:%s' % (T[0],tmp))
        # Check for custom actions
        custom = []
        xitems = []
        for T in items:
            if cfg.has_section(T[1]):
                CA = prepCustomAction(cfg.items(T[1]))
                if CA is None:
                    die('incomplete custom action %s' % T)
                custom.append((T[0],CA['version'],CA['run']))
            else:
                xitems.append(T)

        pkgs,missing = mgr.getPackageInfo(xitems, options.debug);
        selections.append((mgr, pkgs, missing, custom))

    if options.pkglist:
        # First print packages not installed
        for mgr,pkgs,missing,custom in selections:
            print('%s PACKAGES' % mgr.getName().upper())
            for p in pkgs:
                if not options.verbose:
                    if not p.isInstalled():
                        print('  _ %s' % p.getName())
                elif p.isOnHold():
                    print('  h %s' % p.getName())
                elif p.isInstalled():
                    print('  i %s' % p.getName())
                else:
                    print('  _ %s' % p.getName())
            for m in missing:
                print('  m %s' % m[0])
            for c in custom:
                print('  c %s' % c[0])

    if options.pkginstall:
        for mgr,pkgs,missing,custom in selections:
            # Install packages first
            todo, update = mgr.prepareInstall(pkgs)
            if len(todo) == 0 and len(update) == 0:
                print('Packages up to date - no action required')
            else:
                mgr.installPackages(packageList=todo, update=len(update) != 0, debug=options.debug, verbose=options.verbose)
                mgr.refreshPackageCandidates(update)
                todo, update = mgr.prepareInstall(update)
                mgr.installPackages(packageList=todo, update=False, debug=options.debug, verbose=options.verbose)
                if len(update) !=0:
                    warning('unable to satisfy all package constraints')
                    printPackageInfo(update)

            # Now handle custom actions
            caPkgs,caMissing = mgr.getPackageInfo(custom, options.debug)
            todo, update = mgr.prepareInstall(caPkgs)
            if len(caMissing) != 0 or len(update) != 0:
                for ca in custom:
                    exe_path = os.path.join(base_path, ca[2])
                    if os.path.isfile(exe_path):
                        if not mgr.executeAsRoot(exe_path, debug=options.debug, verbose=options.verbose):
                            die('execution failed %s' % exe_path)
                    else:
                        die('cannot locate custom action %s' % exe_path)
            elif len(todo) == 0:
                print('Custom packages up to date - no action required')
            else:
                mgr.installPackages(packageList=todo, update=len(update) != 0, debug=options.debug, verbose=options.verbose)
                mgr.refreshPackageCandidates(update)
                todo, update = mgr.prepareInstall(update)
                mgr.installPackages(packageList=todo, update=False, debug=options.debug, verbose=options.verbose)
                if len(update) !=0:
                    warning('unable to satisfy all package constraints for custom actions')
                    printPackageInfo(update)

            # if we had missing custom packages must do one more retry
            if len(caMissing) > 0:
                caPkgs,caMissing = mgr.getPackageInfo(custom, options.debug)
                todo, updateRequired = mgr.prepareInstall(caPkgs)
                mgr.installPackages(packageList=todo, update=True, debug=options.debug, verbose=options.verbose)
                caPkgs,caMissing = mgr.getPackageInfo(custom, options.debug)
                if len(caMissing):
                    warning('cannot resolve missing packages %s' % str(caMissing))

