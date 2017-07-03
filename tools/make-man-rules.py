#!/usr/bin/env python3
#  -*- Mode: python; coding: utf-8; indent-tabs-mode: nil -*- */
#
#  This file is part of systemd.
#
#  Copyright 2013, 2017 Zbigniew Jędrzejewski-Szmek
#
#  systemd is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.
#
#  systemd is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with systemd; If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import collections
import sys
import os.path
import pprint
from xml_helper import *

def man(page, number):
    return '{}.{}'.format(page, number)

def xml(file):
    return os.path.basename(file)

def add_rules(rules, name):
    xml = xml_parse(name)
    # print('parsing {}'.format(name), file=sys.stderr)
    if xml.getroot().tag != 'refentry':
        return
    conditional = xml.getroot().get('conditional') or ''
    rulegroup = rules[conditional]
    refmeta = xml.find('./refmeta')
    title = refmeta.find('./refentrytitle').text
    number = refmeta.find('./manvolnum').text
    refnames = xml.findall('./refnamediv/refname')
    target = man(refnames[0].text, number)
    if title != refnames[0].text:
        raise ValueError('refmeta and refnamediv disagree: ' + name)
    for refname in refnames:
        assert all(refname not in group
                   for group in rules.values()), "duplicate page name"
        alias = man(refname.text, number)
        rulegroup[alias] = target
        # print('{} => {} [{}]'.format(alias, target, conditional), file=sys.stderr)

def create_rules(xml_files):
    " {conditional => {alias-name => source-name}} "
    rules = collections.defaultdict(dict)
    for name in xml_files:
        try:
            add_rules(rules, name)
        except Exception:
            print("Failed to process", name, file=sys.stderr)
            raise
    return rules

def mjoin(files):
    return ' \\\n\t'.join(sorted(files) or '#')

MESON_HEADER = '''\
# Do not edit. Generated by make-man-rules.py.
manpages = ['''

MESON_FOOTER = '''\
]
# Really, do not edit.'''

def make_mesonfile(rules, dist_files):
    # reformat rules as
    # grouped = [ [name, section, [alias...], condition], ...]
    #
    # but first create a dictionary like
    # lists = { (name, condition) => [alias...]
    grouped = collections.defaultdict(list)
    for condition, items in rules.items():
        for alias, name in items.items():
            group = grouped[(name, condition)]
            if name != alias:
                group.append(alias)

    lines = [ [p[0][:-2], p[0][-1], sorted(a[:-2] for a in aliases), p[1]]
              for p, aliases in sorted(grouped.items()) ]
    return '\n'.join((MESON_HEADER, pprint.pformat(lines)[1:-1], MESON_FOOTER))

if __name__ == '__main__':
    pages = sys.argv[1:]

    rules = create_rules(pages)
    dist_files = (xml(file) for file in pages
                  if not file.endswith(".directives.xml") and
                     not file.endswith(".index.xml"))
    print(make_mesonfile(rules, dist_files))
