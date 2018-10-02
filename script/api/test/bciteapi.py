#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2016, Silvio Peroni <essepuntato@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright notice
# and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
# DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
# SOFTWARE.

__author__ = "essepuntato"

import unittest
from script.api.bciteapi import create_br, call_crossref, fix_reference
from time import time
from urllib.parse import quote


class BCiteAPITest(unittest.TestCase):

    def setUp(self):
        self.json = '{"volume": "1","publisher": "ABIS-AlmaDL ","issue": "1","title": "dsdfe",' \
                    '"doi": "10.4403/jlis.it-12419","author": ["Citti, Francesco"],' \
                    '"journal": "Conservation Science in Cultural Heritage","year": "2008"}'
        self.time = time()
        self.base = "http://localhost:8000/corpus/"
        self.citing = "br/1"
        self.cited = "br/5"
        self.style = "chicago"
        self.accept = "true"
        self.reference = quote("Peroni, S., Shotton, D. (2012). FaBiO and CiTO: ontologies for describing "
                               "bibliographic resources and citations. In Journal of Web Semantics: Science, "
                               "Services and Agents on the World Wide Web, 17 (December 2012): 33-43. Amsterdam, "
                               "The Netherlands: Elsevier. DOI: 10.1016/j.websem.2012.08.001")
        self.reference_changed = quote("It works like a charme!")

    def create_br(self):
        self.assertEqual(create_br(self.time, self.json), (self.time, self.base + self.citing))

    def call_crossref(self):
        self.assertEqual(call_crossref(self.time, self.citing, self.style, self.reference),
                         (self.time, self.citing, self.style, self.base + self.cited))

    def fix_reference(self):
        self.assertNotEqual(fix_reference(self.time, self.accept, self.citing, self.cited, self.reference_changed)[4],
                            self.reference_changed)

    def test_bcite(self):
        with self.subTest("create_br"):
            self.create_br()
        with self.subTest("call_crossref"):
            self.call_crossref()
        with self.subTest("fix_reference"):
            self.fix_reference()


if __name__ == "__main__":
    unittest.main()
