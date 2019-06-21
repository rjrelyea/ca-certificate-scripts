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


read_into_array('old-ca-bundle.crt', old_file)
read_into_array('trusted_all_bundle', new_file)

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
