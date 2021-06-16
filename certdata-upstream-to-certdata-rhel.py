#!/usr/bin/python2
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
o.add_option('--without-disable-after', dest="with_disable_after", action="store_false", default=True)
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
    if echo_line and not in_multiline_skip:
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
            obj = dict()
            in_obj = False
            in_trust = False
            in_cert = False
            has_tls_trust = False
            legacy_server = ""
            legacy_email = ""
        continue

    if in_multiline or in_multiline_skip:
        if not line.startswith('END'):
            if type == 'MULTILINE_OCTAL':
                line = line.strip()
                for i in re.finditer(r'\\([0-3][0-7][0-7])', line):
                    value += chr(int(i.group(1), 8))
            else:
                value += line
            continue
        if in_multiline :
            obj[field] = value
        if in_multiline :
            echo_line = False
        in_multiline = False
        in_multiline_skip = False
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

    if field == 'CKA_NSS_MOZILLA_CA_POLICY' and not options.with_ca_policy:
        # Skip if we don't have options.with_ca_policy.
        echo_line = False
        continue
    if re.match('CKA_.*_DISTRUST_AFTER',field) and not options.with_distrust_after:
        if type == 'MULTILINE_OCTAL':
            # some distrust after entries are MULTI_LINE, we want to drop
            # everything
            in_multiline_skip = True
            value = ""
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

