Updating the CA trust list in RHEL
Author: Kai Engert
Date: August/September/October 2018

Updating the CA trust list in RHEL

1. Introduction
2. Distribution mechanics
3. Related background information
4. Script certdata-upstream-to-certdata-rhel.py
5. RHEL 5
App A. Script doit.sh
App B. Script sort-bundle.py
App C. 2019 Update with new scripts

1. Introduction

In RHEL we ship Mozilla’s CA certificate trust list, which is used to verify
certificates used on the public Internet. It contains separate trust settings
for server certificates (for verifying SSL/TLS servers) and email certificates
(for verifying email correspondents). In past versions, it also contained
separate trust settings for code signing.

In RHEL, the Mozilla CA trust list is distributed separately from
Firefox/Thunderbird.

We used to ship two copies of the CA trust list, in two separate packages, in
different formats.


The following packages distribute the CA trust list, based on RHEL version:

                RHEL5  RHEL6  RHEL7  RHEL8
openssl           X
ca-certificates          X      X      X
nss               X      X      X

Because some applications (or configurations) consume the list only from one
of the distributed formats, we always update all packages.

Common motivations for updating the CA trust list in RHEL are:
* Firefox got updated on a RHEL branch and contains an updated CA list.
This happens at least once per year.
* Ensure that software on older RHEL branch retains the ability to communicate
  with other systems that use current certificates.
Product management prefers a yearly update of all EUS[a]/etc. Branches.
* A security incident.

[a]Active EUS releases are at:
https://access.redhat.com/support/policy/updates/errata/

Whenever engineering considers an update to the CA trust list, historically,
engineering has proactively filed bugs and contacted product managers for
approval.


Here are links to lists of bugs from past update cycles:
   * http://etherpad.corp.redhat.com/firefox-52-2-ca-updates
   * http://etherpad.corp.redhat.com/firefox-60-ca-updates

2. Distribution mechanics

The RHEL distribution of the CA trust list is based on files certdata.txt and
nssckbi.h (version number), which are part of Mozilla NSS releases. Usually,
(except for openssl on RHEL 5), files certdata.txt+nssckbi.h are copied into
the distribution directory of an RPM package, and the package build script
creates the format required for distribution.

For compatibility reasons, RHEL branches may use a modified version of the CA
trust list, which contains one or more of the following changes:
   * trust older CA certificates that use 1024-bit RSA keys, which are no
longer trusted by Mozilla.
   * trust CAs for code signing
   * Include or exclude a PKCS#11 attribute that flags a CA as originating
from Mozilla’s trust list

Because RHEL’s CA trust modifications might be considered a less secure
configuration by customers, newer RHEL branches offer a configuration choice
using the ca-legacy configuration tool.  This requires to distribute the CA
trust list in two variations, which either uses RHEL’s modifications, or the
unmodified Mozilla CA trust list. This is implemented by including multiple
trust clags in the source certdata.txt text file. Only the ca-certificates
package supports this configuration mechanism.

The following table shows the modifications to certdata.txt based on RHEL
version:

Package:
ca-certificates     Add        Add      ca-legacy   ca-policy
                   1024-bit  codesign   choice      attribute
---------------------------------------------------------------
RHEL 7.6            no         no         yes        yes
RHEL 7.5
---------------------------------------------------------------
RHEL 6.10           yes        yes        yes        yes
---------------------------------------------------------------
RHEL 7.4            no         yes        yes        yes
---------------------------------------------------------------
RHEL 7.3            yes        yes        yes        no
RHEL 7.2
---------------------------------------------------------------
RHEL 6.5            yes        yes        no         no
---------------------------------------------------------------

Package:
openssl             Add        Add      ca-legacy   ca-policy
                   1024-bit  codesign   choice      attribute
---------------------------------------------------------------
RHEL 5.11          yes         no         no         no
---------------------------------------------------------------

Package:
nss                 Add        Add      ca-legacy   ca-policy
                   1024-bit  codesign   choice      attribute
---------------------------------------------------------------
RHEL 7.6           no          no         no         yes
RHEL 7.5
---------------------------------------------------------------
RHEL 7.4           no          yes        no         yes
---------------------------------------------------------------
RHEL 7.3           no          yes        no         no
RHEL 7.2
RHEL 5.11
---------------------------------------------------------------

A script called certdata-upstream-to-certdata-rhel.py has been developed,
 which can be used to convert a certdata.txt file from the upstream NSS code
distribution, and apply the above modifications. The resulting file can then
be used as the input for the ca-certificates or nss source RPM packages.

Parameter --add-legacy-1024bit will add the reference file
   certdata-legacy-1024bit-rsa.txt.

Parameter --add-legacy-codesign will set code signing trust flags based on
   reference file certdata-2.14-code-signing-trust.txt.

The above flags support, and will use, separate LEGACY_CKA_TRUST_* flags,
to offer the ca-legacy configuration choice.

Parameter --without-legacy-choice will remove the CKA_TRUST_* trust flags,
and use the contents of the LEGACY_CKA_TRUST_* flags as CKA_TRUST_* trust.

Parameter --without-ca-policy-attribute can be used to exclude the PKCS#11
attribute CKA_NSS_MOZILLA_CA_POLICY if the distribution doesn’t use or doesn’t
support it.

3. Related background information

Starting with RHEL 6.5, we introduced a mechanism that allows a centrally
configured CA trust list. It is described in the update-ca-trust manual page.
In short, it uses directory hierarchies of master (source) files, and a
mechanism to make it available in multiple file formats (extracted), and also
using a PKCS#11 API.

Historically, the primary users of the PKCS#11 API were applications that are
based on the NSS crypto library. This API has been implemented using the NSS
library libnssckbi.so. Over time, some other applications also switched to
read the CA trust list from this API, such as the gnutls library on newer RHEL
versions.

The historical implementation of libnssckbi.so, as provided by NSS, uses
static contents, which are defined at package build time.

In order to introduce a universal and flexible configuration mechanism for
administrators, RHEL 6.5 and newer provide the p11-kit-trust.so module, which
emulates the classic PKCS#11 API of the libnssckbi.so module.

The following table shows the availability of the PKCS#11 APIs:

                Static               Dynamic             Default
              libnssckbi.so        libnssckbi.so
              is available         is available
             (provided by NSS)     (emulated using
                                p11-kit-trust.so)
----------------------------------------------------------------
RHEL 5             X                   -                 static
----------------------------------------------------------------
RHEL 6.0 to 6.4    X                   -                 static
----------------------------------------------------------------
RHEL 6.5+ 64-bit   X                   X                 static
----------------------------------------------------------------
RHEL 6.5+ multilib X                   -                 static
(32-bit on 64-bit               (distribution bug)
host)
----------------------------------------------------------------
RHEL 7.0 to 7.5    X                   X                 dynamic
64-bit
----------------------------------------------------------------
RHEL 7.0 to 7.5    X                   -                 static
multilib (32-bit               (distribution bug)
on 64-bit host)
----------------------------------------------------------------
RHEL 7.6+          X                   X                 dynamic
----------------------------------------------------------------
RHEL 8             -                   X                 dynamic
----------------------------------------------------------------

On RHEL 6.x and RHEL 7.x, a low-level configuration mechanism exists, which
allows an administrator to configure which of these modules should be used by
applications that access the PKCS#11 API. It is implemented using the general
update-alternatives configuration tool. Administrators probably rarely use
this mechanism. The mechanism is automatically used by the package
installation scripts, and also define which one is used by default, by
assigning priority levels. However, a missing package (such as a missing
32-bit architecture package on a 64-bit host), can cause the lower priority
alternative to be used, if the higher priority alternative isn’t available.

On RHEL 6.x, for backwards compatibility reasons, the static NSS module is
used by default.

On RHEL 6.x only (not RHEL 7), a high level configuration mechanism is used
(on top of the above low-level mechanism).
Admins can opt in to the newer, more flexible configuration with command
“update-ca-trust enable”. The configuration can be checked using
“update-ca-trust check”. Documentation can be found with “man update-ca-trust”.

That RHEL 6.x configuration isn’t limited to the PKCS#11 API. It also controls
symbolic links, for well known filenames, which point to files in PEM file
format or Java keyring file format.

The following table shows what those files contain, depending on configuration.
                     RHEL 5    RHEL 6.0-6.4    RHEL 6.5+    RHEL 7    RHEL 8
-----------------------------------------------------------------------------
As distributed         X             X            X
with package, or                               (default
manually changed by                          configuration:
user.                                           DISABLE)
Treated as config files,
never updated by RPM after
manual change.
-----------------------------------------------------------------------------
Created using the                                 X            X         X
update-ca-trust script
which combines distributed                     (opt-in
CA trust with local                            configuration:
system configuration.                            ENABLE)
-----------------------------------------------------------------------------

Because RHEL 6 uses the static NSS module by default, updates to RHEL 6 should
be shipped for both the ca-certificates and the nss packages.

Because of the distribution bug on RHEL 7.0 to RHEL 7.5, which prevents
32-bit applications from using the dynamic PKCS#11 trust list API, updates to
RHEL <=7.5 should be shipped for both the ca-certificates and the nss
packages. (The same distribution exists on all RHEL 6.x versions, which means
the argument also applies to RHEL 6.5+.)

Because the static NSS module is still available in RHEL 7.6+, and some
applications might ignore the system configuration and explicitly choose to
open the module contained in the NSS package, updates to the CA trust list on
RHEL >=7.6 should be shipped for both the ca-certificates and the nss packages.

I recommend to read my justification in
https://bugzilla.redhat.com/show_bug.cgi?id=1446636 why updating the CA list
in openssl on rhel 5 is useful.

Note this changelog item, which explains why one of the legacy CA seems to be
contained twice:
* Thu Dec 04 2014 Kai Engert <kaie@redhat.com> - 2014.1.98-65.2
- Add an alternative version of the "Thawte Premium Server CA" root,
  which carries a SHA1-RSA signature, to allow OpenJDK to verify applets
  which contain that version of the root certificate (rhbz#1138230).
  This change doesn't add trust for another key, because both versions
  of the certificate use the same public key.

Hint: When building ca-certificates on RHEL 6, it will regularly fail, because
it requires jdk, which is only available for i386 or x86_64. There’s no way to
require such a buildhost. You must repeatedly submit the build, until you’re
lucky and get a builder of the supported architecture.

RHEL 5
Use the old branch ca-certificates/rhel-6.6 for preparing the ca trust data for
openssl on rhel 5


Edit ca-certificates.spec and disable/remove the following line:
#BuildRequires: java-1.6.0-openjdk
#BuildRequires: asciidoc

Use the new upstream certdata.txt that you want to use as input for RHEL 5, and
perform this initial preparation step (using the script we described in the
previous chapter):

./certdata-upstream-to-certdata-rhel.py --input new-upstream-certdata.txt --output prepared-for-rhel5-certdata.txt --add-legacy-1024bit --without-legacy-choice --without-ca-policy-attribute

Copy the resulting prepared-for-rhel5-certdata.txt into the
ca-certificates/rhel-6.6 directory as file certdata.txt, and also copy
 nssckbi.h from upstream.

Execute command:
rhpkg local
We don’t care about the resulting rpm file it creates. We’re interested in the
temporary data that the build scripts created in subdirectory ca-certificates,
which we will process further, so later failures are not a problem.

Obtain the script described as: "helper script to combine output of
certdata2pem.py".
See bug 1200263 comment 9, which contains attachment 1016079.
https://bugzilla.redhat.com/attachment.cgi?id=1016079

Save the file, filename "doit.sh", into the ca-certificates subdirectory (which
was created by the previous command), and execute it:
chmod +x doit.sh
./doit.sh

It creates a new file: trusted_all_bundle

We’re almost done. As a last step, we sort this file, using an old file as a
reference.

(The sorting isn't required for functionality, but it allows you to more easily
compare and review the update.)

To perform the sorting, get the script described as: "helper script to create
identically sorted files".
See bug 1200263 comment 10, which contains attachment 1016080.
https://bugzilla.redhat.com/attachment.cgi?id=1016080

Save the file, filename "sort-bundle.py" and save it into the same
subdirectory.

Copy the previously shipped rhel 5 bundle to the same directory.
cp openssl/rhel-5.11/ca-bundle.crt old-rhel5-bundle.crt

Edit file sort-bundle.py to adjust filenames
read_into_array('old-rhel5-bundle.crt', old_file)
read_into_array('trusted_all_bundle', new_file)

Run
python sort-bundle.py

It creates new file: sorted-new
This is what you want for the rhel 5 package.

To review, compare old-rhel5-bundle.crt with sorted-new

To use it, copy file sorted-new to openssl/rhel-5.11/ca-bundle.crt



App A. Script certdata-upstream-to-certdata-rhel.py

#!/usr/bin/python
#
# certdata-upstream-to-certdata-rhel.py
# Copyright (C) 2017-2018 Kai Engert <kaie@redhat.com>
#
# A script that modifies upstream certdata.txt and adjusts it for the
# needs of the ca-certificates / nss packages in RHEL.
#
# File was based on certdata-code-signing-compatibility.py,
# which was based on certdata2pem, which was
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


import base64
import os.path
import re
import sys
import textwrap
import urllib
from optparse import OptionParser


o = OptionParser()
o.add_option('--add-legacy-1024bit', dest="add_legacy_1024bit", action="store_true", default=False)
o.add_option('--add-legacy-codesign', dest="add_legacy_codesign", action="store_true", default=False)
o.add_option('--without-legacy-choice', dest="with_legacy_choice", action="store_false", default=True)
o.add_option('--without-ca-policy-attribute', dest="with_ca_policy", action="store_false", default=True)
o.add_option('--input', dest="input", action="store", default="upstream-certdata.txt")
o.add_option('--output', dest="output", action="store", default="rhel-certdata.txt")
o.add_option('--legacy-codesign-input', dest="legacy_codesign_input", action="store", default="certdata-2.14-code-signing-trust.txt")
o.add_option('--legacy-1024bit-input', dest="legacy_1024bit_input", action="store", default="certdata-legacy-1024bit-rsa.txt")


(options,args) = o.parse_args( sys.argv[1:] )
#print (options)


def make_issuer_serial_key(obj):
        return obj['CKA_ISSUER'] + obj['CKA_SERIAL_NUMBER']


codesign_reference_objects = []
in_data, in_multiline, in_obj = False, False, False
field, type, value, obj = None, None, None, dict()
in_trust = False


# PHASE: prepare code_signing_whitelist
# algorithm:
#go through options.legacy_codesign_input (which is a reference file,
# the latest upstream certdata that included code signing trust bits)
#if CKA_CLASS is CKO_NSS_TRUST
#and CKA_TRUST_CODE_SIGNING is CKT_NSS_TRUSTED_DELEGATOR
#then add CKA_ISSUER + CKA_SERIAL_NUMBER to code-signing-whitelist
#
#later we go through new certdata.txt
#if CKA_CLASS is CKO_NSS_TRUST
#and CKA_TRUST_SERVER_AUTH is CKT_NSS_TRUSTED_DELEGATOR
#get new CKA_ISSUER + CKA_SERIAL_NUMBER
#if code-signing-whitelist contains CKA_ISSUER + CKA_SERIAL_NUMBER,
#then set CKA_TRUST_CODE_SIGNING to CKT_NSS_TRUSTED_DELEGATOR


code_signing_whitelist = set()
if options.add_legacy_codesign:
        for line in open(options.legacy_codesign_input, 'r'):
            # Ignore the file header.
            if not in_data:
                if line.startswith('BEGINDATA'):
                    in_data = True
                continue
            # Ignore comment lines.
            if line.startswith('#'):
                continue
            # Empty lines are significant if we are inside an object.
            if len(line.strip()) == 0:
                if in_obj:
                    # end of object reached, add it, and reset
                    codesign_reference_objects.append(obj)
                    obj = dict()
                    in_obj = False
                    in_trust = False
                continue


            if in_multiline:
                if not line.startswith('END'):
                    if type == 'MULTILINE_OCTAL':
                        line = line.strip()
                        for i in re.finditer(r'\\([0-3][0-7][0-7])', line):
                            value += chr(int(i.group(1), 8))
                    else:
                        value += line
                    continue
                obj[field] = value
                in_multiline = False
                continue
            if line.startswith('CKA_CLASS'):
                in_obj = True
            line_parts = line.strip().split(' ', 2)
            if len(line_parts) > 2:
                field, type = line_parts[0:2]
                value = ' '.join(line_parts[2:])
            elif len(line_parts) == 2:
                field, type = line_parts
                value = None
            else:
                raise NotImplementedError, 'line_parts < 2 not supported.\n' + line


            if field == 'CKA_CLASS' and value == 'CKO_NSS_TRUST':
                in_trust = True


            if in_trust:
                if field == 'CKA_TRUST_CODE_SIGNING' and value == 'CKT_NSS_TRUSTED_DELEGATOR':
                    key = make_issuer_serial_key(obj)
                    code_signing_whitelist.add(key)


            if type == 'MULTILINE_OCTAL':
                in_multiline = True
                value = ""
                continue
            obj[field] = value


        # end of file reached, add the started obj, if it has data
        if len(obj.items()) > 0:
            codesign_reference_objects.append(obj)
# end of PHASE: prepare code_signing_whitelist


out = open(options.output, 'w')


# PHASE: convert input
# algorithm:
# Write out all data from the input file, and process as requested
# (adding codesigning, adding/removing ca-policy attribute,
#  and add trust either with always-legacy using standard trust flags,
#  or configure trust with legacy choice)


in_data, in_multiline, in_obj = False, False, False
field, type, value, obj = None, None, None, dict()
in_trust = False
in_cert = False
has_tls_trust = False


echo_line = False
previous_line = ""
legacy_server = ""
legacy_email = ""


for line in open(options.input, 'r'):
        if echo_line:
            out.write(previous_line)


        echo_line = True
        previous_line = line


        # Ignore the file header.
        if not in_data:
            if line.startswith('BEGINDATA'):
                in_data = True
            continue
        # Ignore comment lines.
        if line.startswith('#'):
            continue
        # Empty lines are significant if we are inside an object.
        if len(line.strip()) == 0:
            if in_obj:
                # end of object reached, add it, and reset
                if in_cert and options.with_ca_policy:
                    out.write("CKA_NSS_MOZILLA_CA_POLICY CK_BBOOL CK_TRUE\n")
                obj = dict()
                in_obj = False
                in_trust = False
                in_cert = False
                has_tls_trust = False
                legacy_server = ""
                legacy_email = ""
            continue


        if in_multiline:
            if not line.startswith('END'):
                if type == 'MULTILINE_OCTAL':
                    line = line.strip()
                    for i in re.finditer(r'\\([0-3][0-7][0-7])', line):
                        value += chr(int(i.group(1), 8))
                else:
                    value += line
                continue
            obj[field] = value
            in_multiline = False
            continue
        if line.startswith('CKA_CLASS'):
            in_obj = True
        line_parts = line.strip().split(' ', 2)
        if len(line_parts) > 2:
            field, type = line_parts[0:2]
            value = ' '.join(line_parts[2:])
        elif len(line_parts) == 2:
            field, type = line_parts
            value = None
        else:
            raise NotImplementedError, 'line_parts < 2 not supported.\n' + line


        if field == 'CKA_NSS_MOZILLA_CA_POLICY':
            # Skip. We'll add that later, if requested by options.with_ca_policy
            echo_line = False
            continue


        if field == 'CKA_CLASS':
            if value == 'CKO_NSS_TRUST':
                in_trust = True
            elif value == 'CKO_CERTIFICATE':
                in_cert = True


        if in_trust:
            # This script strictly relies on the ordering of the trust
            # attributes in certdata.txt, it assumes that CKA_TRUST_SERVER_AUTH
            # is listed before CKA_TRUST_CODE_SIGNING.


            if field == 'CKA_TRUST_SERVER_AUTH':
                legacy_server = "LEGACY_" + line
                if value == 'CKT_NSS_TRUSTED_DELEGATOR':
                    has_tls_trust = True


            if field == 'CKA_TRUST_EMAIL_PROTECTION':
                legacy_email = "LEGACY_" + line


            if field == 'CKA_TRUST_CODE_SIGNING' and has_tls_trust:
                key = make_issuer_serial_key(obj)
                # if options.add_legacy_codesign is false, then code_signing_whitelist is empty
                # and the existing line will be used
                if key in code_signing_whitelist:
                    echo_line = False
                    if (options.with_legacy_choice):
                        out.write(line)
                        out.write(legacy_server);
                        out.write(legacy_email);
                        out.write("LEGACY_CKA_TRUST_CODE_SIGNING " + type + " CKT_NSS_TRUSTED_DELEGATOR\n")
                    else:
                        out.write("CKA_TRUST_CODE_SIGNING " + type + " CKT_NSS_TRUSTED_DELEGATOR\n")


        if type == 'MULTILINE_OCTAL':
            in_multiline = True
            value = ""
            continue
        obj[field] = value


if echo_line:
        out.write(previous_line)
if in_cert and options.with_ca_policy:
        out.write("CKA_NSS_MOZILLA_CA_POLICY CK_BBOOL CK_TRUE\n")
# end of PHASE: convert input


# PHASE: append 1024bit with adjustments
# We don't adjust the codesigning attributes for the 1024bit CAs.
# We do add the ca-policy attribute if necessary.
# We adjust the trust based on options.with_legacy_choice


in_multiline, in_obj = False, False
field, type, value, obj = None, None, None, dict()
in_trust = False
in_cert = False


echo_line = False
previous_line = ""
legacy_server = ""
legacy_email = ""


if options.add_legacy_1024bit:
        for line in open(options.legacy_1024bit_input, 'r'):
            if echo_line:
                out.write(previous_line)


            echo_line = True
            previous_line = line


            # Ignore comment lines.
            if line.startswith('#'):
                continue
            # Empty lines are significant if we are inside an object.
            if len(line.strip()) == 0:
                if in_obj:
                    # end of object reached, add it, and reset
                    if in_cert and options.with_ca_policy:
                        out.write("CKA_NSS_MOZILLA_CA_POLICY CK_BBOOL CK_TRUE\n")
                    obj = dict()
                    in_obj = False
                    in_trust = False
                    in_cert = False
                    legacy_server = ""
                    legacy_email = ""
                continue


            if in_multiline:
                if not line.startswith('END'):
                    if type == 'MULTILINE_OCTAL':
                        line = line.strip()
                        for i in re.finditer(r'\\([0-3][0-7][0-7])', line):
                            value += chr(int(i.group(1), 8))
                    else:
                        value += line
                    continue
                obj[field] = value
                in_multiline = False
                continue
            if line.startswith('CKA_CLASS'):
                in_obj = True
            line_parts = line.strip().split(' ', 2)
            if len(line_parts) > 2:
                field, type = line_parts[0:2]
                value = ' '.join(line_parts[2:])
            elif len(line_parts) == 2:
                field, type = line_parts
                value = None
            else:
                raise NotImplementedError, 'line_parts < 2 not supported.\n' + line


            if field == 'CKA_NSS_MOZILLA_CA_POLICY':
                # Skip. We'll add that later, if requested by options.with_ca_policy
                echo_line = False
                continue


            if field == 'CKA_CLASS':
                if value == 'CKO_NSS_TRUST':
                    in_trust = True
                elif value == 'CKO_CERTIFICATE':
                    in_cert = True


            if in_trust and not options.with_legacy_choice:
                # This script strictly relies on the ordering of the trust
                # attributes in certdata.txt, it assumes that CKA_TRUST_SERVER_AUTH
                # is listed before CKA_TRUST_CODE_SIGNING.
                # remove CKA_TRUST_*; change LEGACY_CKA_TRUST_* to CKA_TRUST_*


                if (field == 'CKA_TRUST_SERVER_AUTH' or
                    field == 'CKA_TRUST_EMAIL_PROTECTION' or
                    field == 'CKA_TRUST_CODE_SIGNING'):
                    echo_line = False
                    continue


                if (field == 'LEGACY_CKA_TRUST_SERVER_AUTH' or
                    field == 'LEGACY_CKA_TRUST_EMAIL_PROTECTION' or
                    field == 'LEGACY_CKA_TRUST_CODE_SIGNING'):
                    # strip 'LEGACY_' from beginning of the line that will get echoed
                    remainder_start_position = len('LEGACY_')
                    previous_line = previous_line[remainder_start_position:]


            if type == 'MULTILINE_OCTAL':
                in_multiline = True
                value = ""
                continue
            obj[field] = value


        if echo_line:
            out.write(previous_line)
        if in_cert and options.with_ca_policy:
            out.write("CKA_NSS_MOZILLA_CA_POLICY CK_BBOOL CK_TRUE\n")


# end of PHASE: append 1024bit with adjustments


out.close()



App B. Script doit.sh
rm neutral
rm info.trust
rm info.distrust
rm info.notrust
rm trusted_all_bundle
touch neutral
for f in certs/*.crt; do
  echo "processing $f"
  tbits=`sed -n '/^# openssl-trust/{s/^.*=//;p;}' $f`
  distbits=`sed -n '/^# openssl-distrust/{s/^.*=//;p;}' $f`
  alias=`sed -n '/^# alias=/{s/^.*=//;p;q;}' $f | sed "s/'//g" | sed 's/"//g'`
  targs=""
  if [ -n "$tbits" ]; then
     for t in $tbits; do
        targs="${targs} -addtrust $t"
     done
     echo "trust flags $targs for $f" >> info.trust
     #openssl x509 -text -in "$f" -trustout $targs -setalias "$alias" >> trusted_all_bundle
     openssl x509 -text -fingerprint -md5 -in "$f" >> trusted_all_bundle
  fi
  if [ -n "$distbits" ]; then
     for t in $distbits; do
        targs="${targs} -addreject $t"
     done
     echo "disttrust flags $targs for $f" >> info.distrust
  fi

  if [ -z "$targs" ]; then
     echo "no trust flags for $f" >> info.notrust
     # p11-kit-trust defines empty trust lists as "rejected for all purposes".
     # That's why we use the simple file format
     #   (BEGIN CERTIFICATE, no trust information)
     # because p11-kit-trust will treat it as a certificate with neutral trust.
     # This means we cannot use the -setalias feature for neutral trust certs.
     openssl x509 -text -fingerprint -md5 -in "$f" >> neutral
  fi
done



Script sort-bundle.py
#!/usr/bin/python
# vim:set et sw=4:
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

import base64
import os.path
import re
import sys
import textwrap
import urllib
import tempfile
import commands
import os

import epdb
#epdb.set_trace()

old_file = []
new_file = []

field, type, value, obj = None, None, None, dict()

def read_into_array( filename, array ):
   pem = "";
   in_pem = False
   for line in open(filename, 'r'):
       # Ignore comment lines.
       if line.startswith('#'):
           continue
       line = line.strip()
       if len(line) == 0:
           continue
       if not in_pem and line == "-----BEGIN CERTIFICATE-----":
           in_pem = True;
           pem = line + "\n";
           continue
       if in_pem and line == "-----END CERTIFICATE-----":
           in_pem = False;
           pem += line + "\n";
           array.append(pem);
           continue
       if not in_pem:
           continue;
       pem += line + "\n";

def add_cert_to_file(cert_pem_string, file_handle):
   tf = tempfile.NamedTemporaryFile(delete=False)
   tf.write(cert_pem_string)
   tf.flush()
   tf.close()
   output = commands.getoutput("openssl x509 -text -fingerprint -md5 -in %s" % (tf.name))
   file_handle.write(output)
   file_handle.write("\n")
   os.unlink(tf.name)

def output_into_file( filename, array ):
   f = open(filename, 'w')
   for obj in array:
       add_cert_to_file(obj, f)
   f.close()


read_into_array('old-ca-bundle-pre-2.3.crt', old_file)
read_into_array('unsorted-ca-bundle-2.3.crt', new_file)

output_into_file('test-old', old_file)
#output_into_file('test-new', new_file)

f = open('sorted-new', 'w');

only_in_new = []
in_new_and_old = []

for new in new_file:
   found = False
   for old in old_file:
       if old == new:
           found = True
           break
   if found:
       in_new_and_old.append(new)
   else:
       only_in_new.append(new)

for old in old_file:
   for found_in_new in in_new_and_old:
       if old == found_in_new:
           add_cert_to_file(old, f)

for new in only_in_new:
   add_cert_to_file(new, f)

f.close()

App C. 2019 Update with new scripts

build_combo.sh updates all the requested releases based on the requirements
described in this document:

 usage: ./build_comb.sh [-r] [-t nss_type] [-n nss_release] [-f] rhel_releases
  -d               use the development tip rather than the latest release
  -n nss_release   fetch a specific nss release (default latest)
  -t nss_type      type of nss release to fetch (RTM,BETA1,BETA2)
  -f cert_datadir  fetch certdata.txt, nssckbi.h, and nss.h from a directory

Running ./build_comb.sh rhel-5.11 rhel-6.10 rhel-7.4 rhel-7.6 rhel-8.0.0

Will automatically pull the latest released certdata.txt from mozilla and
update openssl/rhel-5.11 nss/rhel-5.11/nss nss/rhel-6.10 nss/rhel-7.4 
nss/rhel-7.6 ca-certificates/rhel-6.10 ca-certificates/rhel-7.4 
ca-certificates/rhel-7.6 ca-certificates-rhel-8.0.0 which the appropriate
certdata.txt or bundle.crt files. The respective .spec files will be updated
with a new descriptive log entry, and all the files will be marked for checkin.

If you want to pull the latest development version of certdata.txt use -d.
If you want to pull a specific version of nss use -n release and -t nss_type.
If you alread have your certdata.txt, you can use -f to point to the directory
where you've placed certdata.txt. NOTE: you also need the corresponding 
nssckbi.h and nss.h in that directory as well.

Checkin and pushs are not done by the command, but a list of modified packages
are printed at the end. A checkin message is prebuild into the file checkin.log

Sample output of ./build_comb.sh:
./build_combo.sh rhel-5.11 rhel-6.10 rhel-7.4 rhel-7.5 rhel-7.6 rhel-7.7 rhel-8.0.0 rhel-8.1.0
******************************************************************
*                   Setting up directories                       *
******************************************************************
******************************************************************
*                   Fetching Sources                             *
******************************************************************
>> fetching ca-certificates
X11 forwarding request failed on channel 0
>> fetching nss
X11 forwarding request failed on channel 0
>> fetching openssl
X11 forwarding request failed on channel 0
******************************************************************
*          Modifying certdata.txt for releases                   *
******************************************************************
******************************************************************
*          Updating RHEL packages                                *
******************************************************************
************************** openssl rhel-5.11 ****************************
>>> fetching rhel-6.6 ca-certificates
>>> build ca-certificates.spec with the new spec

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD5withRSA signature algorithm which is considered a security risk.

Warning:
The input uses the MD2withRSA signature algorithm which is considered a security risk.
/var/tmp/rpm-tmp.GKcbTu: line 162: asciidoc.py: command not found
error: Bad exit status from /var/tmp/rpm-tmp.GKcbTu (%build)
    Bad exit status from /var/tmp/rpm-tmp.GKcbTu (%build)
Could not execute local: rpmbuild --define '_sourcedir /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6' --define '_specdir /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6' --define '_builddir /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6' --define '_srcrpmdir /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6' --define '_rpmdir /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6' --define 'dist .el6_6' --define 'rhel 6' --define 'el6_6 1' --quiet -ba /home/builds/ca-certificates/ca-certificate-scripts/scratch.26151/rhel-6.6/ca-certificates.spec | tee .build-2017.2.14-65.0.1.el6_6.log
>>> use the ca-certificates build to create an openssl bundle.
>>> verify against the old bundle.
>>> update openssl.spec
diff --git a/openssl.spec b/openssl.spec
index 6699502..19af55a 100644
--- a/openssl.spec
+++ b/openssl.spec
@@ -21,7 +21,7 @@
 Summary: The OpenSSL toolkit
 Name: openssl
 Version: 0.9.8e
-Release: 43%{?dist}
+Release: 44%{?dist}
 # The tarball is based on the openssl-fips-1.2.0-test.tar.gz tarball
 Source: openssl-fips-%{version}-usa.tar.bz2
 Source1: hobble-openssl
@@ -497,6 +497,36 @@ rm -rf $RPM_BUILD_ROOT/%{_bindir}/openssl_fips_fingerprint
 %postun -p /sbin/ldconfig
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 0.9.8e-44
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+     C=US, O=VISA, OU=Visa International Service Association, CN=Visa eCommerce Root
+     C=CO, O=Sociedad Cameral de Certificaci\xC3\xB3n Digital - Certic\xC3\xA1mara S.A., CN=AC Ra\xC3\xADz Certic\xC3\xA1mara S.A.
+     CN=ComSign CA, O=ComSign, C=IL
+     C=DE, O=Deutscher Sparkassen Verlag GmbH, OU=S-TRUST Certification Services, CN=S-TRUST Universal Root CA
+     C=DE, O=TC TrustCenter GmbH, OU=TC TrustCenter Class 3 CA, CN=TC TrustCenter Class 3 CA II
+     C=FR, O=Certplus, CN=Certplus Root CA G1
+     C=FR, O=Certplus, CN=Certplus Root CA G2
+     C=FR, O=OpenTrust, CN=OpenTrust Root CA G1
+     C=FR, O=OpenTrust, CN=OpenTrust Root CA G2
+     C=FR, O=OpenTrust, CN=OpenTrust Root CA G3
+     C=TR, L=Ankara, O=T\xC3\x9CRKTRUST Bilgi \xC4\xB0leti\xC5\x9Fim ve Bili\xC5\x9Fim G\xC3\xBCvenli\xC4\x9Fi Hizmetleri A.\xC5\x9E., CN=T\xC3\x9CRKTRUST Elektronik Sertifika Hizmet Sa\xC4\x9Flay\xC4\xB1c\xC4\xB1s\xC4\xB1 H5
+   Adding:
+     C=FR, O=Dhimyotis, OU=0002 48146308100036, CN=Certigna Root CA
+     C=US, OU=emSign PKI, O=eMudhra Inc, CN=emSign ECC Root CA - C3
+     C=IN, OU=emSign PKI, O=eMudhra Technologies Limited, CN=emSign ECC Root CA - G3
+     C=US, OU=emSign PKI, O=eMudhra Inc, CN=emSign Root CA - C1
+     C=IN, OU=emSign PKI, O=eMudhra Technologies Limited, CN=emSign Root CA - G1
+     OU=GlobalSign Root CA - R6, O=GlobalSign, CN=GlobalSign
+     C=US, O=Google Trust Services LLC, CN=GTS Root R1
+     C=US, O=Google Trust Services LLC, CN=GTS Root R2
+     C=US, O=Google Trust Services LLC, CN=GTS Root R3
+     C=US, O=Google Trust Services LLC, CN=GTS Root R4
+     C=HK, ST=Hong Kong, L=Hong Kong, O=Hongkong Post, CN=Hongkong Post Root CA 3
+     C=CH, O=WISeKey, OU=OISTE Foundation Endorsed, CN=OISTE WISeKey Global Root GC CA
+     C=CN, O=UniTrust, CN=UCA Extended Validation Root
+     C=CN, O=UniTrust, CN=UCA Global G2 Root
+
 * Fri Dec 21 2018 Bob Relyea <rrelyea@redhat.com> 0.9.8e-43
 - Rebase ca-bundle.crt to the upstream version 2.22 with legacy
   modifications. For compatibility reasons, several CA certificates with
# On branch rhel-5.11
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	modified:   ca-bundle.crt
#	modified:   openssl.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
**************************** nss rhel-5.11 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
>>> generating patch file nss-rhel-5.11-ca-2.32.patch
>>> update nss.spec
>>> verify updated nss.spec
diff --git a/nss.spec b/nss.spec
index efa292d..6105766 100644
--- a/nss.spec
+++ b/nss.spec
@@ -10,7 +10,7 @@
 Summary:          Network Security Services
 Name:             nss
 Version:          3.21.4
-Release:          4%{?dist}
+Release: 5%{?dist}
 License:          MPLv2.0
 URL:              http://www.mozilla.org/projects/security/pki/nss/
 Group:            System Environment/Libraries
@@ -76,6 +76,8 @@ Patch50:          new-mechanisms.patch
 # For CVE-2015-2730 and CVE-2015-2721
 # from https://hg.mozilla.org/projects/nss/rev/2c05e861ce07
 Patch102:         CheckForPeqQ-or-PnoteqQ-before-adding-P-and-Q.patch
+# Update certdata.txt to version 2.32
+Patch103: nss-rhel-5.11-ca-2.32.patch
 
 ################### nss patches
 Patch22:           dont-include-sysinit.patch
@@ -288,6 +290,7 @@ popd
 pushd nss
 %patch220 -p1 -b .pay-pal-oid-update
 popd
+%patch103 -p1 -b .ca-2.32
 
 # Apply the patches to the tree where we build freebl/softoken
 cd nss-softokn-util-%{fips_source_version}
@@ -1024,6 +1027,36 @@ done
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 3.21.4-5
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Fri Dec 21 2018 Bob Relyea <rrelyea@redhat.com> - 3.21.4-4
 - Update Paypal certs for tests
 
# On branch rhel-5.11
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	new file:   nss-rhel-5.11-ca-2.32.patch
#	modified:   nss.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
#	nss-3.21.4-4.el5_11.src.rpm
**************************** nss rhel-6.10 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
>>> generating patch file nss-rhel-6.10-ca-2.32.patch
>>> update nss.spec
>>> verify updated nss.spec
diff --git a/nss.spec b/nss.spec
index 9a25ed9..9639bc1 100644
--- a/nss.spec
+++ b/nss.spec
@@ -24,7 +24,7 @@
 Summary:          Network Security Services
 Name:             nss
 Version:          3.36.0
-Release:          9%{?dist}
+Release: 10%{?dist}
 License:          MPLv2.0
 URL:              http://www.mozilla.org/projects/security/pki/nss/
 Group:            System Environment/Libraries
@@ -104,6 +104,8 @@ Patch52: Bug-1001841-disable-sslv2-libssl.patch
 Patch53: Bug-1001841-disable-sslv2-tests.patch
 # Upstream: https://bugzilla.mozilla.org/show_bug.cgi?id=943144
 Patch62: nss-fix-deadlock-squash.patch
+# Update certdata.txt to version 2.32
+Patch63: nss-rhel-6.10-ca-2.32.patch
 
 # Local patch to deal with current older version of softoken/freebl
 Patch69: define-uint32.patch
@@ -313,6 +315,7 @@ pushd nss
 %patch229 -p1 -b .ssl2-server-random
 popd
 %patch221 -p1 -b .pem-decoding
+%patch63 -p1 -b .ca-2.32
 
 #########################################################
 # Higher-level libraries and test tools need access to
@@ -891,6 +894,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 3.36.0-10
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Tue Aug 28 2018 Daiki Ueno <dueno@redhat.com> - 3.36.0-9
 - Backport upstream fix for CVE-2018-12384
 - Remove nss-lockcert-api-change.patch, which turned out to be a
# On branch rhel-6.10
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	new file:   nss-rhel-6.10-ca-2.32.patch
#	modified:   nss.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
#	nss-3.36.0-9.el6_10.src.rpm
********************** ca-certificaes rhel-6.10 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index 1e29cd1..61487d7 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -47,11 +47,11 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.22
+Version: 2019.2.32
 # On RHEL 6.x, please keep the release version < 70
 # When rebasing on Y-Stream (6.y), use 65.1, 65.2, 65.3, ...
 # When rebasing on Z-Stream (6.y.z), use 65.0, 65.0.1, 65.0.2, ...
-Release: 65.1%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -505,6 +505,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Wed Feb 28 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-65.1
 - Update to CKBI 2.22 from NSS 3.35 with legacy modifications.
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-6.10
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
**************************** nss rhel-7.4 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
>>> generating patch file nss-rhel-7.4-ca-2.32.patch
>>> update nss.spec
>>> verify updated nss.spec
diff --git a/nss.spec b/nss.spec
index be492d1..67fdb2d 100644
--- a/nss.spec
+++ b/nss.spec
@@ -27,7 +27,7 @@
 Summary:          Network Security Services
 Name:             nss
 Version:          3.28.4
-Release:          15.1%{?dist}
+Release: 16%{?dist}
 License:          MPLv2.0
 URL:              http://www.mozilla.org/projects/security/pki/nss/
 Group:            System Environment/Libraries
@@ -166,6 +166,8 @@ Patch144: nss-pk12util-faulty-aes.patch
 Patch150: nss-3.28.4-certdata-v.2.22.patch
 # update pay pal certs
 Patch155: nss-tests-paypal-certs-v2.patch
+# Update certdata.txt to version 2.32
+Patch156: nss-rhel-7.4-ca-2.32.patch
 
 %description
 Network Security Services (NSS) is a set of libraries designed to
@@ -288,6 +290,7 @@ popd
 pushd nss
 %patch155 -p1 -b .paypal
 popd
+%patch156 -p1 -b .ca-2.32
 
 #########################################################
 # Higher-level libraries and test tools need access to
@@ -877,6 +880,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 3.28.4-16
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Fri Dec 21 2018 Bob Relyea <rrelyea@redhat.com> - 3.28.4-15.2
 - Update paypal certs to builds will work
 
# On branch rhel-7.4
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	new file:   nss-rhel-7.4-ca-2.32.patch
#	modified:   nss.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
#	nss-3.28.4-15.1.el7_4.src.rpm
********************** ca-certificaes rhel-7.4 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index 7971f18..eb8041d 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,11 +35,11 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.22
+Version: 2019.2.32
 # On RHEL 7.x, please keep the release version >= 70
 # When rebasing on Y-Stream (7.y), use 71, 72, 73, ...
 # When rebasing on Z-Stream (7.y.z), use 70.0, 70.1, 70.2, ...
-Release: 70.0%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -358,6 +358,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Mon Dec 10 2018 Bob Relyea <rrellyea@redhat.com> - 2018.2.22-70.0
 - Update to CKBI 2.20 from NSS 3.36
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-7.4
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
**************************** nss rhel-7.5 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
>>> generating patch file nss-rhel-7.5-ca-2.32.patch
>>> update nss.spec
>>> verify updated nss.spec
diff --git a/nss.spec b/nss.spec
index d117328..daa8af7 100644
--- a/nss.spec
+++ b/nss.spec
@@ -27,7 +27,7 @@
 Summary:          Network Security Services
 Name:             nss
 Version:          3.36.0
-Release:          7%{?dist}
+Release: 8%{?dist}
 License:          MPLv2.0
 URL:              http://www.mozilla.org/projects/security/pki/nss/
 Group:            System Environment/Libraries
@@ -139,6 +139,8 @@ Patch141: nss-sysinit-getenv.patch
 Patch142: nss-ssl2-server-random.patch
 # Upstream: https://bugzilla.mozilla.org/show_bug.cgi?id=1444960
 Patch143: nss-tests-ssl-normal-normal.patch
+# Update certdata.txt to version 2.32
+Patch144: nss-rhel-7.5-ca-2.32.patch
 
 %description
 Network Security Services (NSS) is a set of libraries designed to
@@ -250,6 +252,7 @@ pushd nss
 %patch142 -p1 -b .ssl2-server-random
 %patch143 -p1 -b .tests-ssl-normal-normal
 popd
+%patch144 -p1 -b .ca-2.32
 
 #########################################################
 # Higher-level libraries and test tools need access to
@@ -849,6 +852,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 3.36.0-8
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Wed Aug 29 2018 Daiki Ueno <dueno@redhat.com> - 3.36.0-7
 - Backport upstream fix for CVE-2018-12384
 - Remove nss-lockcert-api-change.patch, which turned out to be a
# On branch rhel-7.5
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	new file:   nss-rhel-7.5-ca-2.32.patch
#	modified:   nss.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
#	nss-3.36.0-7.el7_5.src.rpm
********************** ca-certificaes rhel-7.5 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index de7e9dc..338a77d 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,11 +35,11 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.22
+Version: 2019.2.32
 # On RHEL 7.x, please keep the release version >= 70
 # When rebasing on Y-Stream (7.y), use 71, 72, 73, ...
 # When rebasing on Z-Stream (7.y.z), use 70.0, 70.1, 70.2, ...
-Release: 70.0%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -358,6 +358,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Wed Mar 14 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-70.0
 - Update to CKBI 2.22 from NSS 3.35
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-7.5
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
**************************** nss rhel-7.6 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
>>> generating patch file nss-rhel-7.6-ca-2.32.patch
>>> update nss.spec
>>> verify updated nss.spec
diff --git a/nss.spec b/nss.spec
index 2ad67f6..3e37877 100644
--- a/nss.spec
+++ b/nss.spec
@@ -27,7 +27,7 @@
 Summary:          Network Security Services
 Name:             nss
 Version:          3.36.0
-Release:          7.1%{?dist}
+Release: 8%{?dist}
 License:          MPLv2.0
 URL:              http://www.mozilla.org/projects/security/pki/nss/
 Group:            System Environment/Libraries
@@ -142,6 +142,8 @@ Patch141: nss-sysinit-getenv.patch
 Patch142: nss-ssl2-server-random.patch
 # Upstream: https://bugzilla.mozilla.org/show_bug.cgi?id=1444960
 Patch143: nss-tests-ssl-normal-normal.patch
+# Update certdata.txt to version 2.32
+Patch144: nss-rhel-7.6-ca-2.32.patch
 
 %description
 Network Security Services (NSS) is a set of libraries designed to
@@ -257,6 +259,7 @@ pushd nss
 %patch142 -p1 -b .ssl2-server-random
 %patch143 -p1 -b .tests-ssl-normal-normal
 popd
+%patch144 -p1 -b .ca-2.32
 
 #########################################################
 # Higher-level libraries and test tools need access to
@@ -856,6 +859,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 3.36.0-8
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Mon Nov 12 2018 Bob Relyea <rrelyea@redhat.com> - 3.36.0-7.1
 - Update the cert verify code to allow a new ipsec usage and follow RFC 4945
 
# On branch rhel-7.6
# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#
#	new file:   nss-rhel-7.6-ca-2.32.patch
#	modified:   nss.spec
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
#	nss-3.36.0-7.1.el7_6.src.rpm
********************** ca-certificaes rhel-7.6 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index de7e9dc..338a77d 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,11 +35,11 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.22
+Version: 2019.2.32
 # On RHEL 7.x, please keep the release version >= 70
 # When rebasing on Y-Stream (7.y), use 71, 72, 73, ...
 # When rebasing on Z-Stream (7.y.z), use 70.0, 70.1, 70.2, ...
-Release: 70.0%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -358,6 +358,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Wed Mar 14 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-70.0
 - Update to CKBI 2.22 from NSS 3.35
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-7.6
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
**************************** nss rhel-7.7 ******************************
Fetch and extract the current nss build
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
######################################################################## 100.0%
Skipping nss build for rhel-7.7. certdata is already up to date
********************** ca-certificaes rhel-7.7 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index de7e9dc..338a77d 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,11 +35,11 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.22
+Version: 2019.2.32
 # On RHEL 7.x, please keep the release version >= 70
 # When rebasing on Y-Stream (7.y), use 71, 72, 73, ...
 # When rebasing on Z-Stream (7.y.z), use 70.0, 70.1, 70.2, ...
-Release: 70.0%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -358,6 +358,36 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "TC TrustCenter Class 3 CA II"
+    # Certificate "ComSign CA"
+    # Certificate "S-TRUST Universal Root CA"
+    # Certificate "TÜRKTRUST Elektronik Sertifika Hizmet Sağlayıcısı H5"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Wed Mar 14 2018 Kai Engert <kaie@redhat.com> - 2018.2.22-70.0
 - Update to CKBI 2.22 from NSS 3.35
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-7.7
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
********************** ca-certificaes rhel-8.0.0 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index 056f8e5..152a5b5 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,10 +35,10 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.24
+Version: 2019.2.32
 # for Rawhide, please always use release >= 2
 # for Fedora release branches, please use release < 2 (1.0, 1.1, ...)
-Release: 6%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -372,6 +372,33 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "ComSign CA"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Mon Aug 13 2018 Tomáš Mráz <tmraz@redhat.com> - 2018.2.24-6
 - Use __python3 macro when invoking Python
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-8.0.0
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
********************** ca-certificaes rhel-8.1.0 *************************
>>> update ca-certificates.spec file
New Version: 2019.2.32
diff --git a/ca-certificates.spec b/ca-certificates.spec
index 5f3aee4..a165d8a 100644
--- a/ca-certificates.spec
+++ b/ca-certificates.spec
@@ -35,10 +35,10 @@ Name: ca-certificates
 # to have increasing version numbers. However, the new scheme will work, 
 # because all future versions will start with 2013 or larger.)
 
-Version: 2018.2.24
+Version: 2019.2.32
 # for Rawhide, please always use release >= 2
 # for Fedora release branches, please use release < 2 (1.0, 1.1, ...)
-Release: 6.1%{?dist}
+Release: 1%{?dist}
 License: Public Domain
 
 Group: System Environment/Base
@@ -372,6 +372,33 @@ fi
 
 
 %changelog
+*Fri Jun 21 2019 Bob Relyea <rrelyea@redhat.com> - 2019.2.32-1
+Update to CKBI 2.32 from NSS 3.44
+   Removing:
+    # Certificate "Visa eCommerce Root"
+    # Certificate "AC Raiz Certicamara S.A."
+    # Certificate "ComSign CA"
+    # Certificate "Certplus Root CA G1"
+    # Certificate "Certplus Root CA G2"
+    # Certificate "OpenTrust Root CA G1"
+    # Certificate "OpenTrust Root CA G2"
+    # Certificate "OpenTrust Root CA G3"
+   Adding:
+    # Certificate "GlobalSign Root CA - R6"
+    # Certificate "OISTE WISeKey Global Root GC CA"
+    # Certificate "GTS Root R1"
+    # Certificate "GTS Root R2"
+    # Certificate "GTS Root R3"
+    # Certificate "GTS Root R4"
+    # Certificate "UCA Global G2 Root"
+    # Certificate "UCA Extended Validation Root"
+    # Certificate "Certigna Root CA"
+    # Certificate "emSign Root CA - G1"
+    # Certificate "emSign ECC Root CA - G3"
+    # Certificate "emSign Root CA - C1"
+    # Certificate "emSign ECC Root CA - C3"
+    # Certificate "Hongkong Post Root CA 3"
+
 * Fri May 10 2019 Robert Relyea <rrelyea@redhat.com> - 2018.2.24-6.1
 - Test gating
 
fatal: pathspec 'ca-certificate.spec' did not match any files
# On branch rhel-8.1.0
# Changes not staged for commit:
#   (use "git add <file>..." to update what will be committed)
#   (use "git checkout -- <file>..." to discard changes in working directory)
#
#	modified:   ca-certificates.spec
#	modified:   certdata.txt
#
# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	checkin.log
no changes added to commit (use "git add" and/or "git commit -a")
Finished updates with 0 errors
The following directories are ready for checkin:
packages/ca-certificates/rhel-6.10
packages/ca-certificates/rhel-7.4
packages/ca-certificates/rhel-7.5
packages/ca-certificates/rhel-7.6
packages/ca-certificates/rhel-7.7
packages/ca-certificates/rhel-8.0.0
packages/ca-certificates/rhel-8.1.0
packages/nss/rhel-5.11
packages/nss/rhel-6.10
packages/nss/rhel-7.4
packages/nss/rhel-7.5
packages/nss/rhel-7.6
packages/openssl/rhel-5.11


