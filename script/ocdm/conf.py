#!/usr/bin/python
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

triplestore_url = "http://localhost:9999/blazegraph/sparql"
triplestore_url_real = "http://localhost:9999/blazegraph/sparql"
context_path = "https://w3id.org/oc/corpus/context.json"
base_iri = "http://localhost:8000/corpus/"
orcid_conf_path = "./script/spacin/orcid_conf.json"
dataset_home = "http://opencitations.net/"
dir_split_number = 10000  # This must be multiple of the following one
items_per_file = 1000
doi_curator = "BCite"
doi_provider = "BCite"
bcite_base_iri = "http://localhost:8000"
temp_dir_for_rdf_loading = "./"
base_dir = "./corpus/"
info_dir = base_dir + "id-counter/"
context_file_path = base_dir + "context.json"
default_dir = "_"
full_info_dir = info_dir + default_dir + "/"


