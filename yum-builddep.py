#!/usr/bin/python -tt

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sys, os

sys.path.insert(0, '/usr/share/yum-cli')
import cli
import yum
import rpmUtils
import yum.Errors
import logging
from optparse import OptionParser

def parseArgs():
    usage = "usage: %s [options] package1 [package2] [package..]" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("--repoid", default=[], dest="repos", action="append", 
      help='operate on a specific repo, can be specified multiple times', 
      metavar='[repo]')
    (opts, args) = parser.parse_args()
    if len(args) < 1: 
        parser.print_help()
        sys.exit(0)
    return (opts, args)

def main():
    logger = logging.getLogger("yum.verbose.yumbuilddep")
    opts, args = parseArgs()
    base = cli.YumBaseCli()
    base.doConfigSetup(init_plugins=True,
                       plugin_types=(yum.plugins.TYPE_CORE,))
    base.conf.uid = os.geteuid()
        
    if base.conf.uid != 0:
        logger.info("You must be root to install packages")
        sys.exit(1)

    if len(opts.repos) > 0:
        for repo in base.repos.findRepos('*'):
            if repo.id not in opts.repos:
                repo.disable()
            else:
                repo.enable()

    archlist = rpmUtils.arch.getArchList() + ['src']
    base.doRepoSetup(dosack=0)
    base.doTsSetup()
    base.doRpmDBSetup()
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    
    base.doSackSetup(archlist)

    srcnames = []
    srpms = []
    for arg in args:
        if arg.endswith('.src.rpm'):
            srpms.append(yum.packages.YumLocalPackage(ts, arg))
        elif arg.endswith('.src'):
            srcnames.append(arg)
        else:
            srcnames.append('%s.src' % arg)

    exact, match, unmatch = yum.packages.parsePackages(base.pkgSack.returnPackages(), srcnames, casematch=1)
    srpms += exact + match
    if len(unmatch) > 0:
        logger.error("No such package(s): %s" % ", ".join(unmatch))
        sys.exit(1)

    for srpm in srpms:
        for dep in srpm.requiresList():
            if dep.startswith("rpmlib("): continue
            try:
                pkg = base.returnPackageByDep(dep)
                if not base.rpmdb.installed(name=pkg.name):
                    base.tsInfo.addInstall(pkg)
            except yum.Errors.PackageSackError, e:
                logger.error("Error: %s" % e)
                sys.exit(1)
                    
    (result, resultmsgs) = base.buildTransaction()
    if len(base.tsInfo) == 0:
        logger.info("Nothing to do")
    else: 
        base.listTransaction()
        base.doTransaction()



if __name__ == "__main__":
    main()
                
# vim:sw=4:sts=4:expandtab              
