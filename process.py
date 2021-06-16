#!/usr/bin/python
# vim:set et sw=4:
#
# certdata2pem.py - splits certdata.txt into multiple files
#
# Copyright (C) 2009 Philipp Kern <pkern@debian.org>
# Copyright (C) 2013 Kai Engert <kaie@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301,
# USA.

import os.path
import subprocess
import sys
import getopt
import requests
import json
import git
from datetime import date
from requests_kerberos import HTTPKerberosAuth


rhel_list='./meta/rhel.list'
fedora_list='./meta/fedora.list'
ckbiver_file='./meta/ckbiversion.txt'
nssver_file='./meta/nssversion.txt'
firefox_info='./meta/firefox_info.txt'
config_file='./config.cfg'
errata_url_base='https://errata.devel.redhat.com'
bugzilla_url_base='https://bugzilla.redhat.com'
brew_url_base='https://brewweb.engineering.redhat.com/brew'
koji_url_base='https://koji.fedoraproject.org/koji'
ca_certs_file='/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem'
bug_summary_short='Annual %s ca-certificates update'
bug_summary = bug_summary_short+ ' version %s from NSS %s for Firefox %s [%s]'
bug_description='Update CA certificates to version %s from NSS %s for our annual CA certficate update.'
distro=None
packages_dir = {
    "rhel":"./packages/",
    "fedora":"./packages/fedora/"
}
build_info_tool = {
    "rhel":"brew",
    "fedora":"koji"
}
package_tool = {
    "rhel":"rhpkg",
    "fedora":"fedpkg"
}

z_stream_clone = {
    "rhel-5.11":False,
    "rhel-6.10":False,
    "rhel-7.1":True,
    "rhel-7.2":True,
    "rhel-7.3":True,
    "rhel-7.4":True,
    "rhel-7.5":True,
    "rhel-7.6":True,
    "rhel-7.7":True,
    "rhel-7.8":True,
    "rhel-7.9":False,
    "rhel-8.0.0":True,
    "rhel-8.1.0":True,
    "rhel-8.2.0":True,
    "rhel-8.3.0":True,
    "rhel-8.4.0":True,
    "rhel-8.5.0":False
}

bug_version_map = {
    "rhel-5.11":"5.11",
    "rhel-6.10":"6.10",
    "rhel-7.1":"7.1",
    "rhel-7.2":"7.2",
    "rhel-7.3":"7.3",
    "rhel-7.4":"7.4",
    "rhel-7.5":"7.5",
    "rhel-7.6":"7.6",
    "rhel-7.7":"7.7",
    "rhel-7.8":"7.8",
    "rhel-7.9":"7.9",
    "rhel-8.0.0":"8.0",
    "rhel-8.1.0":"8.1",
    "rhel-8.2.0":"8.2",
    "rhel-8.3.0":"8.3",
    "rhel-8.4.0":"8.4",
    "rhel-8.5.0":"8.5",
}
release_map = {
    "rhel-5.11":"RHEL-5-ELS-EXTENSION",
    "rhel-6.10":"RHEL-6-ELS",
    "rhel-7.1":"RHEL-7.1.EUS",
    "rhel-7.2":"RHEL-7.2.EUS",
    "rhel-7.3":"RHEL-7.3.EUS",
    "rhel-7.4":"RHEL-7.4.EUS",
    "rhel-7.5":"RHEL-7.5.EUS",
    "rhel-7.6":"RHEL-7.6.EUS",
    "rhel-7.7":"RHEL-7.7.EUS",
    "rhel-7.8":"RHEL-7.8.EUS",
    "rhel-7.9":"RHEL-7.9.Z",
    "rhel-8.0.0":"RHEL-8.0.0.Z",
    "rhel-8.1.0":"RHEL-8.1.0.Z.EUS",
    "rhel-8.2.0":"RHEL-8.2.0.Z.EUS",
    "rhel-8.3.0":"RHEL-8.3.0.Z",
    "rhel-8.4.0":"RHEL-8.4.0.Z.EUS",
    "rhel-8.5.0":"RHEL-8.5.0.GA"
}

numeric_release_map = {
    "rhel-5.11":1372,
    "rhel-6.10":1335,
    "rhel-7.1":525,
    "rhel-7.2":0,
    "rhel-7.3":0,
    "rhel-7.4":0,
    "rhel-7.5":0,
    "rhel-7.6":0,
    "rhel-7.7":0,
    "rhel-7.8":0,
    "rhel-7.9":1292,
    "rhel-8.0.0":0,
    "rhel-8.1.0":0,
    "rhel-8.2.0":1227,
    "rhel-8.3.0":0,
    "rhel-8.4.0":1467,
    "rhel-8.5.0":1398
}

product_map = {
    "rhel-5.11":"Red Hat Enterprise Linux 5",
    "rhel-6.10":"Red Hat Enterprise Linux 6",
    "rhel-7.1":"Red Hat Enterprise Linux 7",
    "rhel-7.2":"Red Hat Enterprise Linux 7",
    "rhel-7.3":"Red Hat Enterprise Linux 7",
    "rhel-7.4":"Red Hat Enterprise Linux 7",
    "rhel-7.5":"Red Hat Enterprise Linux 7",
    "rhel-7.6":"Red Hat Enterprise Linux 7",
    "rhel-7.7":"Red Hat Enterprise Linux 7",
    "rhel-7.8":"Red Hat Enterprise Linux 7",
    "rhel-7.9":"Red Hat Enterprise Linux 7",
    "rhel-8.0.0":"Red Hat Enterprise Linux 8",
    "rhel-8.1.0":"Red Hat Enterprise Linux 8",
    "rhel-8.2.0":"Red Hat Enterprise Linux 8",
    "rhel-8.3.0":"Red Hat Enterprise Linux 8",
    "rhel-8.4.0":"Red Hat Enterprise Linux 8",
    "rhel-8.5.0":"Red Hat Enterprise Linux 8"
}

release_description_map = {
    "rhel-5.11":"Red Hat Enterprise Linux 5.11",
    "rhel-6.10":"Red Hat Enterprise Linux 6.10",
    "rhel-7.1":"Red Hat Enterprise Linux 7.1 Extended Update Support",
    "rhel-7.2":"Red Hat Enterprise Linux 7.2 Extended Update Support",
    "rhel-7.3":"Red Hat Enterprise Linux 7.3 Extended Update Support",
    "rhel-7.4":"Red Hat Enterprise Linux 7.4 Extended Update Support",
    "rhel-7.5":"Red Hat Enterprise Linux 7.5 Extended Update Support",
    "rhel-7.6":"Red Hat Enterprise Linux 7.6 Extended Update Support",
    "rhel-7.7":"Red Hat Enterprise Linux 7.7 Extended Update Support",
    "rhel-7.8":"Red Hat Enterprise Linux 7.8 Extended Update Support",
    "rhel-7.9":"Red Hat Enterprise Linux 7.9",
    "rhel-8.0.0":"Red Hat Enterprise Linux 8.0.0",
    "rhel-8.1.0":"Red Hat Enterprise Linux 8.1.0 Extended Update Support",
    "rhel-8.2.0":"Red Hat Enterprise Linux 8.2.0 Extended Update Support",
    "rhel-8.3.0":"Red Hat Enterprise Linux 8.3.0",
    "rhel-8.4.0":"Red Hat Enterprise Linux 8.4.0 Extended Update Support",
    "rhel-8.5.0":"Red Hat Enterprise Linux 8"
}

def map_zstream_release(release):
    return release.replace('rhel-','')

package_description_map= {
    "ca-certificates":"The ca-certificates package contains a set of Certificate Authority (CA) certificates chosen by the Mozilla Foundation for use with the Internet Public Key Infrastructure (PKI).",
    "nss":"Network Security Services (NSS) is a set of libraries designed to support the cross-platform development of security-enabled client and server applications.",
    "openssl":"OpenSSL is a toolkit that implements the Secure Sockets Layer (SSL) and Transport Layer Security (TLS) protocols, as well as a full-strength general-purpose cryptography library."
}

# constants
owner=None
manager=None
qe=None
firefox_version=None
bugzilla_login=None
buzilla_password=None
bugzilla_token=None
solution="Before applying this update, make sure all previously released errata relevant to your system have been applied.\n\nFor details on how to apply this update, refer to:\n\nhttps://access.redhat.com/articles/11258"
description_base="Bug Fix(es) and Enhancement(s):\n\n* Update ca-certificates package in %s to CA trust list version (%s) %s from Firefox %s (bug %d)\n"
synopsis="%s bug fix and enhancement update"
topic_base="An update for %s %s now available for %s."
checkin_log="checkin.log"

#
#    Bugzilla helper function
#
# create a new bug
def bug_create(release,version,nss_version,firefox_version,packages,token) :
    packages_list=packages.split(',')
    bug = {}
    bug['product'] = product_map[release]
    bug['component'] = packages_list[0]
    bug['version'] = bug_version_map[release]
    bug['summary'] = bug_summary%(year,version,nss_version,firefox_version,release)
    bug['description'] = bug_description%(version,nss_version)
    bug['priority'] = 'low'
    bug['severify'] = 'low'
    bug['keywords'] = ('Triaged','Rebase')
    bug['status'] = 'NEW'
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=bugzilla_url_base+"/rest/bug"
    if token != None :
        url = url + '?' + token

    print(">>>would create bug with %s and"%url,bug)
    #r = requests.post(url, headers=headers, json=bug,
    #                 verify=ca_certs_file)
    #if r.status_code <= 299 :
    #    return int(r.json()['id'])
    #print('bug create status=%d'%r.status_code)
    #print('returned text=',r.text)
    return 0

# look up a bug based on the description. this is to find cloned z-stream bugs
# which we didn't create from your script
def bug_lookup(release, version, firefox_version, packages, token, zstream):
    packages_list=packages.split(',')
    summary=bug_summary_short%year
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    if zstream :
        login=''
        last="&summary=%s"%release
        if token != None :
           login=token + '&'
           last=''
        url=bugzilla_url_base+"/rest/bug?%sproduct=%s&component=%s&status=NEW&status=ASSIGNED&status=MODIFIED&status=ON_QA&cf_zstream_target_release=%s&cf_internal_target_release=---&limit=1&summary=%s%s"%(login,
            product_map[release], packages_list[0],
            map_zstream_release(release), summary, last)
    else:
        url=bugzilla_url_base+"/rest/bug?product=%s&component=%s&version=%s&status=NEW&status=ASSIGNED&status=MODIFIED&status=ON_QA&limit=1&summary=%s"%(product_map[release],
             packages_list[0],bug_version_map[release],summary)
    r = requests.get(url, headers=headers, verify=ca_certs_file)
    if r.status_code <= 299 :
        bugs = r.json()['bugs']
        if len(bugs) == 0 :
            print("bug for %s %s %s not found"%(release,packages_list[0],version))
            return 0
        return int(bugs[0]['id'])
    print('bug lookup status=%d'%r.status_code)
    print('returned text=',r.text)
    return 0

def bug_login(login, password):
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=bugzilla_url_base+"/rest/login?login=%s&password=%s"%(login,password)
    r = requests.get(url, headers=headers, verify=ca_certs_file)
    if r.status_code <= 299 :
        token = r.json()['token']
        bugzilla_token="token="+token
        return "token="+token
    print('bug login status=%d'%r.status_code)
    print('returned text=',r.text)
    return None

# check if the bug has all it's required acks for checkin
def bug_is_acked(bugnumber, token) :
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=bugzilla_url_base+"/rest/bug/%d"%bugnumber
    if token != None :
        url += '?' + token + '&include_fields=flags'
    else :
        url += '?include_fields=flags'
    r = requests.get(url, headers=headers, verify=ca_certs_file)
    if r.status_code > 299 :
        print('bug acked status=%d'%r.status_code)
        print('bug acked returned text=',r.text)
        return False
    bugs=r.json()['bugs']
    if len(bugs) == 0:
        print("bug %d not found: couldn't check acks"%bugnumber)
        return False
    for flag in bugs[0]['flags'] :
        if flag['status'] == '+' :
            if flag['name'] == 'release' :
                return True
            if flag['name'] == 'rhel-7.9.z' :
                return True
            if flag['name'] == 'rhel-6-els' :
                return True
    return False

def bug_get_state(bugnumber) :
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=bugzilla_url_base+"/rest/bug/%d"%bugnumber
    r = requests.get(url, headers=headers, verify=ca_certs_file)
    if r.status_code <= 299 :
        bugs = r.json()['bugs']
        if len(bugs) == 0 :
            print("bug get state bug %d not found"%bugnumber)
            return 'Unknown'
        return bugs[0]['status']
    print('bug get state status=%d'%r.status_code)
    print('returned text=',r.text)
    return 'Unknown'

def bug_change_state(bugnumber, state, token):
    bug = {}
    bug['status'] = state
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=bugzilla_url_base+"/rest/bug/%d"%bugnumber
    if token != None :
        url = url + '?' + token

    r = requests.put(url, headers=headers, json=bug,
                     verify=ca_certs_file)
    if r.status_code <= 299 :
        return bug_get_state(bugnumber)
    print('bug change state status=%d'%r.status_code)
    print('returned text=',r.text)
    return bug_get_state(bugnumber)

#
#    Errata helper function
#
# create a new errata and attack the bug returns the errata number
def errata_create(release, version, firefox_version, packages, year, bugnumber) :
    release_name=release_map[release]
    release_description=release_description_map[release]
    advisory= dict()
    packages_list=packages.split(',')
    # handle signular and plural verbs, adjust the packages to english
    verb='is'
    package_names=packages
    if len(package_list) != 1 :
       verb='is'
       # replace just the last occurance of , with ' and ' and add a space to
       # the rest of the commas
       package_names=packages[::-1].replace(',',' dna ',1)[::-1].replace(',',', ')
    #build the description
    description=''
    for package in packages_list :
       description=description+package_description[package]+'\n\n'
    description=description+description_base%(release_name,year,version,firefox_version)
    #now build the advisory
    advisory['errata_type']='RHBA'
    advisory['security_impact']='None'
    advisory['solution']=solution;
    advisory['description']=description
    advisory['manager_email']=manager
    advisory['package_owner_email']=owner
    advisory['synopsis']=synopsis%package_names
    advisory['topic']=topic_base%(package_names,verb,release_description, bugnumber)
    advisory['idsfixed']=bugnumber
    errata= {}
    errata['product']='RHEL'
    errata['release']=release_name
    errata['advisory']=advisory
    print("----------Creating errrata for "+release.strip())
    print(">>>would create errrata with %s and"%url,errata)
    #headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    #url=errata_url_base+'/api/v1/erratum'
    #print('url='+url)
    #r = requests.post(url, headers=headers, json=errata,
    #                 auth=HTTPKerberosAuth(),
    #                 verify=ca_certs_file)
    #if r.status_code <= 299 :
    #    return r.json()['id']
    #print('errata create status=%d'%r.status_code)
    #print('returned text=',r.text)
    return 0

def errata_lookup(release, version, firefox_version, packages, bugnumber) :
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    packages_list=packages.split(',')
    search_params="/api/v1/erratum/search?show_state_NEW_FILES=1&show_state_QE=1&product[]=16&release[]=%d&synopsis_text=%s"%(numeric_release_map[release],packages_list[0])
    url=errata_url_base + search_params
    r = requests.get(url, headers=headers,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code > 299 :
        print('errrata lookup status=%d'%r.status_code)
        print('text=',r.text)
        return 0
    data=r.json()['data']
    if len(data) == 0 :
        print("errata for %s %s not found"%(release,packages_list[0]))
        return 0
    return int(data[0]['id'])

# return the nvr of the attached builds
def errata_get_bugs(errata) :
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=errata_url_base+"/api/v1/erratum/%d"%errata
    r = requests.get(url, headers=headers,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code >  299 :
        print('errata get builds status=%d'%r.status_code)
        print('text=',r.text)
        return []
    if len(r.json()) == 0 :
        return []
    errata=r.json()
    if not 'bugs' in errata :
        return []
    bug_list=errata['bugs']['bugs']
    bugs = []
    for bug in bug_list:
        bugs.append(bug['bug']['id'])
    return bugs

# return the nvr of the attached builds
def errata_get_builds(errata, release) :
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=errata_url_base+"/api/v1/erratum/%d/builds"%errata
    r = requests.get(url, headers=headers,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code >  299 :
        print('errata get builds status=%d'%r.status_code)
        print('text=',r.text)
        return []
    if len(r.json()) == 0 :
        return []
    builds = []
    for builditem in r.json()[release_map[release]]['builds'] :
        builds +=  list(builditem.keys())
    return builds

def errata_has_bug(errata, bug) :
    bugs = errata_get_bugs(errata)
    for this_bug in bugs :
        if bug == int(this_bug) :
            return True
    return False

# return True if errata has all the builds attached
def errata_has_builds(errata, release, builds) :
    nvrlist = errata_get_builds(errata, release)
    for build in builds.split(',') :
        if not build in nvrlist :
            return False
    return True

def errata_resync_bug(errata, bug) :
    request= []
    request.append(bug)
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=errata_url_base+"/api/v1/erratum/%d/bug/refresh"%errata
    r = requests.post(url, headers=headers, json=request,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code <= 299 :
        return
    print('errata resync bug status=%d'%r.status_code)
    print('text=',r.text)
    return

# add a bug to the errata
def errata_add_bug(errata, bug, resync) :
    if errata_has_bug(errata, bug) :
        return
    if (resync) :
        errata_resync_bug(errata,bug)
    request= {}
    request['bug'] = bug
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=errata_url_base+"/api/v1/erratum/%d/add_bug"%errata
    r = requests.post(url, headers=headers, json=request,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code <= 299 :
        return
    print('errata add bug status=%d'%r.status_code)
    print('text=',r.text)
    return

# add builds to the errata
def errata_add_builds(errata, release, builds) :
    nvr = errata_get_builds(errata, release)
    request= []
    # only add builds we haven't successfully added yet
    for build in builds.split(',') :
        if not build in nvr :
            entry = dict()
            entry['product_version']=release_map[release]
            entry['build']=build
            request.append(entry)
    # if they are all already added, don't send an empty request
    if len(request) == 0 :
        return 0
    headers= { 'Content-type':'application/json', 'Accept':'application/json' }
    url=errata_url_base+"/api/v1/erratum/%d/add_builds"%errata
    r = requests.post(url, headers=headers, json=request,
                     auth=HTTPKerberosAuth(),
                     verify=ca_certs_file)
    if r.status_code <= 299 :
        return
    print('errata add builds status=%d'%r.status_code)
    print('text=',r.text)
    return

#
#    git helper functions
#
def git_files_exist(diff):
    for cfile in diff.iter_change_type('M'):
        return True
    for cfile in diff.iter_change_type('A'):
        if (cfile != checkin_log):
            return True
    for cfile in diff.iter_change_type('D'):
        return True
    #for cfile in diff.iter_change_type('R'):
    #    return True
    for cfile in diff.iter_change_type('T'):
        return True
    return False

def git_repo_state(repo):
    index = repo.index
    commit = repo.head.commit
    origin = repo.remotes.origin
    branch = repo.active_branch
    # staged means changes need committing
    if git_files_exist(index.diff(None)) :
        return 'staged'
    if git_files_exist(index.diff(commit)) :
        return 'staged'
    # committed mean changes are committed, but not pushed
    if git_files_exist(commit.diff(origin.refs[branch.name])) :
        return 'committed'
    return 'pushed'

def git_get_state(release, package, bugnumber):
    repo = git.Repo(packages_dir[distro]+"%s/%s"%(package,release))
    return git_repo_state(repo)

def git_checkin(release, package, bugnumber):
    gitdir=packages_dir[distro]+"%s/%s"%(package,release)
    repo = git.Repo(gitdir)
    index = repo.index
    # first put all the files in 'staged'
    diff = index.diff(None)
    for cfile in diff.iter_change_type('M'):
        print("Adding modified file",cfile.b_path)
        index.add([cfile.b_path])
    for cfile in diff.iter_change_type('A'):
        if cfile != checkin_log :
            print("Adding new file",cfile)
            index.add(cfile.b_patch)
    for cfile in diff.iter_change_type('D'):
        print("Adding removed file",cfile.a_path)
        index.remove([cfile.a_path])
    for cfile in diff.iter_change_type('T'):
        print("Adding moved file",cfile.b_path)
        index.add([cfile.b_path])
    # now build the log message.
    f=open("%s/%s"%(gitdir,checkin_log),"r")
    message=f.read()
    f.close()
    if bugnumber != -1 :
        message="Resolves: rhbz#%s\n\n"%bugnumber + message
    #do the checkin
    print("checking in:",gitdir)
    index.commit(message)
    return git_repo_state(repo)

def git_push(release, package, bugnumber):
    gitdir=packages_dir[distro]+"%s/%s"%(package,release)
    repo = git.Repo(gitdir)
    repo.remotes.origin.push()
    return git_repo_state(repo)
#
#    local utility functions
#
# do all the packages have builds in the nvrlist
def builds_complete(nvrlist,packages) :
    for package in packages.split(',') :
        found=False
        for nvr in nvrlist.split(',') :
            if nvr.startswith(package) :
                found=True
                break
        if not found :
            return False
    return True

def add_nvr(nvrlist, nvr) :
    if nvr == None or nvr == '' :
       return nvrlist
    if nvrlist == '' :
        return nvr
    nlist=nvrlist.split(',')
    nlist.append(nvr)
    return ','.join(nlist)

# todo use brew rest api?
def build_state(nvr) :
    out=subprocess.Popen("%s buildinfo %s"%(build_info_tool[distro],nvr),shell=True, stdin=None,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,close_fds=True)
    brew_response = out.communicate()[0].decode("utf-8").split('\n')
    if len(brew_response) == 0 :
        return 'Nobuilds'
    if brew_response[0].startswith('No such build:') :
        return 'Nobuilds'
    complete=False
    tag=False
    gating=True
    for line in brew_response :
        line = line.strip()
        if line.startswith('State: ') :
            state = line.replace('State: ','')
            if state == 'COMPLETE' :
                complete=True
            elif state == 'BUILDING' :
                return 'Building'
            elif state == 'CANCELED' :
                return 'Nobuilds'
            elif state == 'FAILED' :
                return 'Failed'
            else :
                return 'Nobuilds'
        if line.startswith('Tags: ') :
            tag=True
            if distro == 'fedora' or line.find('-candidate') != -1 :
                gating=False
        if complete and tag :
            if gating :
                return 'Gating'
            return 'Complete'
    return 'NoBuilds'

#
# merge the different states from 2 different builds
# we return the state that is least further along
# than the other states.
def merge_state(state, state2) :
    # first, states of Complete or None have lowest priority
    if state == None or state == 'Complete':
        return state2
    if state2 == None or state2 == 'Complete':
        return state
    # if they are equal, return them
    if state == state2 :
        return state
    # 'Failed' has the highest precidence
    if state == 'Failed' or state2 == 'Failed' :
        return 'Failed'
    # 'Nobuilds' is next
    if state == 'Nobuilds' or state2 == 'Nobuilds' :
        return 'Nobuilds'
    # now we know that 1) state != state2, and neither
    # is equal to None, 'Complete', 'Failed', or 'Nobuilds'
    # One must be 'Gating' and the other 'Building', 'Building'
    # has precidence
    return 'Building'

def build_nvr(release,package):
    packagedir=packages_dir[distro]+"%s/%s"%(package,release)
    if not os.path.exists(packagedir):
        return None
    if not release in build_nvr.cache :
        build_nvr.cache[release]= {}
    if package in build_nvr.cache[release] :
        return build_nvr.cache[release][package]
    
    pushd=os.getcwd()
    os.chdir(packagedir)

    stream=os.popen("%s verrel"%package_tool[distro])
    nvr = stream.read().strip()
    os.chdir(pushd)
    build_nvr.cache[release][package]=nvr
    return nvr
build_nvr.cache = {}

def build_status(release,package):
    nvr = build_nvr(release,package)
    return build_state(nvr)

# todo use brew rest api?
def build_get_info(release, package) :
    nvr = build_nvr(release, package)
    state = build_state(nvr)

    out=subprocess.Popen("%s buildinfo %s"%(build_info_tool[distro],nvr),shell=True, stdin=None,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,close_fds=True)
    brew_response = out.communicate()[0].decode("utf-8").split('\n')
    if len(brew_response) == 0 :
        return ( '', nvr, state )
    if brew_response[0].startswith('No such build:') :
        return ( '', nvr, state )
    for line in brew_response :
        line = line.strip()
        if line.startswith('Task: ') :
            components=line.split()
            return (components[1], nvr, state)
    return ( '', nvr, state )

# todo use brew rest api?
def build(release,package):
    nvr = build_nvr(release,package)
    if nvr == None :
        print("buildir doesn't exist");
        return ''
    state = build_state(nvr)
    if state == 'Complete' :
        return nvr
    if state == 'Building' or state == 'Gating' :
        return ''
    # for failed, or nobuilds, time to make builds
    packagedir=packages_dir[distro]+"%s/%s"%(package,release)

    pushd=os.getcwd()
    os.chdir(packagedir)
    os.system("%s build"%package_tool[distro])
    os.chdir(pushd)
    state = build_state(nvr)
    if state == 'Complete' :
        return nvr
    # anything else, indicate the builds are not yet done
    return ''

#######################################################
#
# argument parsing and configuration initialization
#
#######################################################
try:
    opts, args = getopt.getopt(sys.argv[1:],"r:o:m:q:v:f:y:e:",)
except getopt.GetoptError as err:
    print(err)
    print(sys.argv[0] + ' [-r rhel.list] [-o owner.email] [-m manager.email] [-q qa.email] [-v ckbi.version] [-f firefox.version] [-y year] [-e errataurlbase] [-b bugzillaurlbase]')
    sys.exit(2)


f = open(ckbiver_file, "r")
version=f.read().strip()
f.close()

f = open(nssver_file, "r")
nss_version=f.read().strip()
f.close()

try:
    f = open(firefox_info, "r")
    firefox_version=f.read().strip()
    f.close()
except :
    print("No firefox_info file ("+firefox_info+") be sure to include -f option to specify the related firefox version on first call")

year=date.today().strftime("%Y")

for config in open(config_file, 'r'):
    ( key, value) = config.strip().split(':',2)
    if key == 'manager':
       manager = value.strip()
    if key == 'owner':
       owner = value.strip()
    if key == 'qe':
       qe = value.strip()
    if key == 'version':
       version = value.strip()
    if key == 'firefox':
       firefox_version = value.strip()
    if key == 'errata_url':
       errata_url_base = value.strip()
    if key == 'bugzilla_url':
       bugzilla_url_base = value.strip()
    if key == 'bugzilla_login':
       bugzilla_login = value.strip()
    if key == 'bugzilla_password':
       bugzilla_password = value.strip()

for opt, arg in opts:
    if opt == '-r' :
        rhel_list = arg
    elif opt == '-o' :
        owner = arg
    elif opt == '-m' :
        manager = arg
    elif opt == '-v' :
        version = arg
    elif opt == '-f' :
        firefox_version = arg
    elif opt == '-y' :
        year = arg
    elif opt == '-e' :
        errata_url_base = arg
    elif opt == '-b' :
        bugzilla_url_base = arg

qe_line=''
if  qe != None :
    qe_line=', "assign_to_email":"'+qe+'"'

if firefox_version == None :
    print("-f not specified!")
    sys.exit(2)

if not os.path.exists(firefox_info) :
    f = open(firefox_info, "w")
    f.write(firefox_version)
    f.close()

if bugzilla_login != None :
    bugzilla_token=bug_login(bugzilla_login,bugzilla_password)

rhel_packages = {}
fedora_packages = {}

#######################################################
#
# read in our status files
#
#######################################################
for rhel_entry in open(rhel_list, 'r'):
    (release, packages, bugnumber, erratanumber, nvr, state) = rhel_entry.strip().split(':')
    entry=dict()
    print('release=',release,'packages=',packages,'bugnumber=',bugnumber,'erratanumber=',erratanumber,'nvr=',nvr,'state=',state)
    entry['packages']=packages
    entry['bugnumber']=int(bugnumber)
    entry['erratanumber']=int(erratanumber)
    entry['nvr']=nvr
    entry['state']=state
    rhel_packages[release]=entry

for fedora_entry in open(fedora_list, 'r'):
    (release, packages, bugnumber, erratanumber, nvr, state) = fedora_entry.strip().split(':')
    entry=dict()
    print('release=',release,'packages=',packages,'bugnumber=',bugnumber,'erratanumber=',erratanumber,'nvr=',nvr,'state=',state)
    entry['packages']=packages
    entry['bugnumber']=int(bugnumber)
    entry['erratanumber']=int(erratanumber)
    entry['nvr']=nvr
    entry['state']=state
    fedora_packages[release]=entry

#######################################################
#
# logic to try to advance the release to the next possible
# level.
#
#######################################################
distro='rhel'
for release in rhel_packages:
    entry=rhel_packages[release]
    print("Processing release <%s>:"%release)
    if entry['state'] == 'complete' :
        print("  * complete!")
        continue
    bugnumber=entry['bugnumber']
    packages=entry['packages']

    print("  * handling bugs")
    if bugnumber == 0 :
        # we need bug numbers so that we can commit our changes
        if z_stream_clone[release] :
            # lookup cloned bug number
            bugnumber=bug_lookup(release,version,firefox_version,packages,bugzilla_token,True)
            if bugnumber == 0 :
                print(">>>>parent bug not cloned yet");
                entry['state']='waiting bug clone'
                continue
            entry['bugnumber']=bugnumber
        else :
            # first lookup the bug to see if it has already been created
            bugnumber=bug_lookup(release,version,firefox_version,packages,None,False)
            if bugnumber == 0:
                # nope, create it now
                bugnumber=bug_create(release,version,nss_version,firefox_version,packages,bugzilla_token)
                if bugnumber == 0 :
                    print(">>>>couldn't create bug");
                    entry['state']='need bug'
                    continue
            entry['bugnumber']=bugnumber
    print("      * bug=%d"%bugnumber)
    # if we are here, we have our bug created for our release, we can check it in
    all_builds_pushed=True
    print("  * checking git tree status")
    for package in packages.split(',') :
        # make sure each package is checked in and built
        git_state = git_get_state(release, package, bugnumber)
        print("      * package<%s> state=%s"%(package,git_state))
        if git_state == 'staged' :
              git_state = git_checkin(release, package, bugnumber)
        if git_state == 'committed' and bug_is_acked(bugnumber,bugzilla_token) :
              print('trying to push')
              git_state = git_push(release, package, bugnumber)
        if git_state != 'pushed' :
              all_builds_pushed=False
        if git_state == 'pushed' and not builds_complete(entry['nvr'],package) :
              nvr = build(release,package)
              entry['nvr'] = add_nvr(nvr,entry['nvr'])
    builds=entry['nvr']
    erratanumber=entry['erratanumber']
    all_builds_complete = builds_complete(builds, packages)
    print("  * setting up state")
    # update our state
    if not bug_is_acked(bugnumber,bugzilla_token):
        entry['state'] = 'bug needs ack'
    elif not all_builds_pushed :
        entry['state'] = 'builds need push'
    elif not all_builds_complete :
        state = None
        for package in packages.split(',') :
            state = merge_state(state, build_status(release,package))
        if state == "Nobuilds" :
            entry['state'] = 'builds not started'
        elif state == "Failed" :
            entry['state'] = 'builds failed'
        elif state == "Building" :
            entry['state'] = 'builds in progress'
        elif state == "Gating" :
            entry['state'] = 'builds in gating'
        elif state == "Complete" :
            entry['state'] = 'builds complete, state error'
        else :
            entry['state'] = 'builds in an unknown state'
    elif erratanumber == 0 :
        entry['state'] = 'needs errata'
    print('  * handling errata')
    bug_state=bug_get_state(bugnumber)
    # once the builds are complete, put the bug in modified state
    bug_resync = False
    if all_builds_pushed and (bug_state == 'NEW' or bug_state == 'ASSIGNED') :
        bug_state = bug_change_state(bugnumber, 'MODIFIED', bugzilla_token)
        bug_resync = True
    # and once our bug is modified, we can create the errata
    erratanumber = errata_lookup(release, version, firefox_version, packages, bugnumber)
    if erratanumber == 0 and bug_state == 'MODIFIED' :
        print("      * creating new errata")
        erratanumber = errata_create(release, version, firefox_version, packages, bugnumber)
    if erratanumber != 0 :
        print("      * errata=%d"%erratanumber)
        entry['erratanumber'] = erratanumber
    # finally, once we have our errata and builds, attach them
    if erratanumber != 0 and (bug_state == 'MODIFIED' or bug_state == 'ON_QA') :
        if not errata_has_bug(erratanumber,bugnumber) :
            print("      * adding bug %d to  errata"%bugnumber)
            errata_add_bug(erratanumber, bugnumber, bug_resync)
    if erratanumber != 0 and all_builds_complete :
        entry['state'] = 'need builds attached'
        if  not errata_has_builds(erratanumber, release, builds):
            print("      * adding builds to errata")
            errata_add_builds(erratanumber, release, builds)
        # finally, once the builds are build and attached to the errata, mark this release complete
        if errata_has_builds(erratanumber, release, builds):
            entry['state'] = "needs bugs attached"
            if  errata_has_bug(erratanumber, bugnumber):
                 entry['state'] = 'complete'

# fedora doesn't need bugs and errata, just git and builds
distro='fedora'
for release in fedora_packages:
    entry=fedora_packages[release]
    print("Processing release <%s>:"%release)
    if entry['state'] == 'complete' :
        print("  * complete!")
        continue
    bugnumber=-1
    packages=entry['packages']
    all_builds_pushed=True
    print("  * checking git tree status")
    for package in packages.split(',') :
        # make sure each package is checked in and built
        git_state = git_get_state(release, package, bugnumber)
        print("      * package<%s> state=%s"%(package,git_state))
        if git_state == 'staged' :
              git_state = git_checkin(release, package, bugnumber)
        if git_state == 'committed':
              print('trying to push')
              git_state = git_push(release, package, bugnumber)
        if git_state != 'pushed' :
              all_builds_pushed=False
        if git_state == 'pushed' and not builds_complete(entry['nvr'],package) :
              nvr = build(release,package)
              entry['nvr'] = add_nvr(nvr,entry['nvr'])
    builds=entry['nvr']
    erratanumber=entry['erratanumber']
    all_builds_complete = builds_complete(builds, packages)
    print("  * setting up state")
    if not all_builds_pushed :
        entry['state'] = 'builds need push'
    elif not all_builds_complete :
        state = None
        for package in packages.split(',') :
            state = merge_state(state, build_status(release,package))
        if state == "Nobuilds" :
            entry['state'] = 'builds not started'
        elif state == "Failed" :
            entry['state'] = 'builds failed'
        elif state == "Building" :
            entry['state'] = 'builds in progress'
        elif state == "Complete" :
            entry['state'] = 'builds complete, state error'
        else :
            entry['state'] = 'builds in an unknown state'
    else :
        entry['state'] = 'complete'

#######################################################
#
# Upate in our status files
#
#######################################################
print("Updating %s"%rhel_list)
f = open(rhel_list,"w")
for release in rhel_packages :
    entry = rhel_packages[release]
    bugnumber=entry['bugnumber']
    erratanumber=entry['erratanumber']
    packages=entry['packages']
    f.write("%s:%s:%d:%d:%s:%s\n"%(release,packages,bugnumber,
            erratanumber,entry['nvr'],entry['state']))
f.close()
print("Updating %s"%fedora_list)
f = open(fedora_list,"w")
for release in fedora_packages :
    entry = fedora_packages[release]
    bugnumber=entry['bugnumber']
    erratanumber=entry['erratanumber']
    packages=entry['packages']
    f.write("%s:%s:%d:%d:%s:%s\n"%(release,packages,bugnumber,
            erratanumber,entry['nvr'],entry['state']))
f.close()


#######################################################
#
# print out in our current status
#
#######################################################
print("Current Status:")
distro='rhel'
for release in rhel_packages :
    entry = rhel_packages[release]
    bugnumber=entry['bugnumber']
    erratanumber=entry['erratanumber']
    packages=entry['packages']
    print("%s: state='%s' bug=%d errata=%d"%(release,entry['state'],bugnumber,erratanumber))
    if bugnumber != 0:
        print("    %s/show_bug.cgi?id=%d"%(bugzilla_url_base,bugnumber))
    if erratanumber != 0:
        print("    %s/advisory/%d"%(errata_url_base,erratanumber))
    for package in packages.split(',') :
        (task, nvr, state) = build_get_info(release, package)
        if (task != '') :
            print("    %s/taskinfo?taskID=%s (%s,%s)"%(brew_url_base,task,nvr,state))

distro='fedora'
for release in fedora_packages :
    entry = fedora_packages[release]
    packages=entry['packages']
    print("%s: state='%s'"%(release,entry['state']))
    for package in packages.split(',') :
        (task, nvr, state) = build_get_info(release, package)
        if (task != '') :
            print("    %s/taskinfo?taskID=%s (%s,%s)"%(koji_url_base,task,nvr,state))
