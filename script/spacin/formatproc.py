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

__author__ = 'essepuntato'
import re
from script.support.reporter import Reporter
from script.ocdm.graphlib import GraphSet
from script.support.support import normalise_ascii as sa
from urllib.parse import quote


class FormatProcessor(object):
    doi_pattern = "[^A-z0-9\.]([0-9]+\.[0-9]+(\.[0-9]+)*/[^%\"# \?<>{}\^\[\]`\|\\\+]+)"
    http_pattern = "(https?://([A-z]|[0-9]|%|&|\?|/|\.|_|~|-|:)+)"

    """This class is the abstract one for any kind of processors."""
    def __init__(self, base_iri, context_base, info_dir, entries, n_file_item, supplier_prefix, agent_id=None):
        self.occ = None
        self.doi = None
        self.pmid = None
        self.pmcid = None
        self.url = None
        self.curator = None
        self.source = None
        self.source_provider = None
        self.entries = None

        if entries is not None:
            if "occ" in entries:
                self.occ = entries["occ"]
            if "doi" in entries:
                self.doi = entries["doi"].lower()
            if "pmid" in entries:
                self.pmid = entries["pmid"]
            if "pmcid" in entries:
                self.pmcid = entries["pmcid"]
            if "url" in entries:
                self.url = entries["url"].lower()
            if "curator" in entries:
                self.curator = entries["curator"]
            if "source" in entries:
                self.source = entries["source"]
            if "source_provider" in entries:
                self.source_provider = entries["source_provider"]
            if "references" in entries:
                self.entries = entries["references"]

        self.name = "SPACIN " + self.__class__.__name__
        self.g_set = GraphSet(base_iri, context_base, info_dir, n_file_item, supplier_prefix)
        self.id = agent_id
        self.repok = Reporter(prefix="[%s - INFO] " % self.name)
        self.repok.new_article()
        self.reperr = Reporter(prefix="[%s - ERROR] " % self.name)
        self.reperr.new_article()

    def process(self):
        pass  # Implemented in the subclasses

    def graph_set(self):
        return self.g_set

    def graphs(self):
        return self.g_set.graphs()

    def message(self, mess):
        return "%s" % mess

    @staticmethod
    def clean_entry(entry):
        return quote(sa(re.sub(":", ",", entry)))

    @staticmethod
    def extract_data(string, pattern):
        if string is not None:
            result = re.search(pattern, string)
            if result:
                return result.group(1)

    @staticmethod
    def extract_doi(string):
        if string is not None:
            result = FormatProcessor.extract_data(string, FormatProcessor.doi_pattern)
            if result:
                result = re.sub("(\.|,)?$", "", result)

            return result

    @staticmethod
    def extract_url(string):
        if string is not None:
            result = FormatProcessor.extract_data(string, FormatProcessor.http_pattern)
            if result:
                result = re.sub("\\\\", "", re.sub("/?\.?$", "", result))

            return result
