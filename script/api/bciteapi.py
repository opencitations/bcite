#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2018, Silvio Peroni <essepuntato@gmail.com>
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
from urllib.parse import unquote, quote
from json import loads
from script.spacin.resfinder import ResourceFinder
from script.spacin.crossrefproc import CrossrefProcessor
from script.spacin.orcidfinder import ORCIDFinder
from script.ocdm.conf import base_iri, context_path, info_dir, orcid_conf_path, items_per_file, triplestore_url, bcite_base_iri, doi_curator, doi_provider, temp_dir_for_rdf_loading, dir_split_number, full_info_dir, default_dir, context_file_path, base_dir
from script.ocdm.crossrefdatahandler import CrossrefDataHandler
from script.ocdm.graphlib import ProvSet
from script.ocdm.storer import Storer
from rdflib import Graph, Literal, URIRef
from script.ocdm.graphlib import GraphEntity
from requests import get
from datetime import datetime
from rdflib.namespace import RDF


cited_doi_query = """SELECT ?cited ?doi WHERE {
    ?citing <%s> ?cited .
    OPTIONAL {
        ?cited <%s> [
            <%s> <%s> ;
            <%s> ?doi
        ]
    }
}""" % (GraphEntity.cites, GraphEntity.has_identifier, GraphEntity.uses_identifier_scheme,
        GraphEntity.doi, GraphEntity.has_literal_value)


def create_resources(json=None):
    rf = ResourceFinder(ts_url=triplestore_url, base_dir=base_dir, base_iri=base_iri, tmp_dir=temp_dir_for_rdf_loading,
                        context_map={context_path: context_file_path}, default_dir=default_dir,
                        dir_split=dir_split_number, n_file_item=items_per_file)
    of = None
    if orcid_conf_path is not None:
        of = ORCIDFinder(orcid_conf_path)
    cp = CrossrefProcessor(base_iri, context_path, info_dir, json, rf, of, items_per_file, "")
    cdh = CrossrefDataHandler(graph_set=cp.graph_set(), resource_finder=rf)

    return rf, of, cp, cdh


def gen_prov_and_store_data(cp, rf, timestamp):
    prov = ProvSet(cp.graph_set(), base_iri, context_path, default_dir, full_info_dir, rf,
                   dir_split_number, items_per_file, "")
    prov.generate_provenance(int(timestamp))

    # Store all the data
    res_storer = Storer(cp.graph_set(),
                        context_map={context_path: context_file_path},
                        dir_split=dir_split_number,
                        n_file_item=items_per_file,
                        default_dir=default_dir)

    prov_storer = Storer(prov,
                         context_map={context_path: context_file_path},
                         dir_split=dir_split_number,
                         n_file_item=items_per_file)

    res_storer.upload_and_store(
        base_dir, triplestore_url, base_iri, context_path,
        temp_dir_for_rdf_loading)

    prov_storer.upload_and_store(
        base_dir, triplestore_url, base_iri, context_path,
        temp_dir_for_rdf_loading)


def create_br(timestamp, json):
    rf, of, cp, cdh = create_resources()

    d = loads(unquote(json))

    res = None

    if "doi" in d:
        res = cp.process_doi(d["doi"], doi_curator, doi_provider)

    if res is None:
        crossref_json = {}
        if "doi" in d:
            crossref_json["DOI"] = d["doi"]
        if "publisher" in d:
            crossref_json["publisher"] = d["publisher"]
        if "title" in d:
            crossref_json["title"] = [d["title"]]
        if "author" in d:
            author_l = []
            for author in d["author"]:
                author_name = author.split(", ")
                author_l.append({"given": author_name[1], "family": author_name[0]})
            if author_l:
                crossref_json["author"] = author_l
        if "journal" in d:
            crossref_json["container-title"] = [d["journal"]]
            crossref_json["type"] = "journal-article"
        if "issue" in d:
            crossref_json["issue"] = d["issue"]
        if "volume" in d:
            crossref_json["volume"] = d["volume"]
        if "year" in d:
            crossref_json["issued"] = {"date-parts": [[int(d["year"])]]}

        res = cdh.process_json(crossref_json, bcite_base_iri, doi_curator, doi_provider, bcite_base_iri)
        gen_prov_and_store_data(cp, rf, timestamp)

    return timestamp, str(res)


def call_crossref(timestamp, citing, style, reference):
    citing_url = base_iri + citing

    r_text = unquote(reference)
    json = {
        "occ": citing_url,
        "references": [
            {
                "bibentry": r_text,
                "process_entry": "True"
            }
        ]
    }

    rf, of, cp, cdh = create_resources(json)
    g_set = cp.process_citing_entity()

    comulative_g = Graph()
    for g in g_set.graphs():
        for triple in g.triples((None, None, None)):
            comulative_g.add(triple)

    cited, doi = list(comulative_g.query(cited_doi_query))[0]
    if doi is None:
        doi = rf.retrieve_doi_string(cited)

    if doi is not None:
        doi_str = str(doi)

        if style == "chicago":
            style_str = "chicago-author-date"
        elif style == "mla":
            style_str = "modern-language-association"
        else:
            style_str = "apa"

        r = get("https://citation.crosscite.org/format?style=%s&lang=en-US&doi=%s" % (style_str, doi_str))
        r.encoding = "UTF-8"
        if r.status_code == 200:
            r_text = r.text.strip()
            for g in g_set.graphs():
                triples = list(g.triples((None, GraphEntity.has_content, None)))
                if len(triples):
                    s, p, o = triples[0]
                    g.remove((s, p, o))
                    g.add((s, p, Literal(r_text)))

    gen_prov_and_store_data(cp, rf, timestamp)

    return timestamp, citing, style, str(cited)


def fix_reference(timestamp, accept, citing, cited, reference):
    rf, of, cp, cdh = create_resources()
    s = Storer(cp.graph_set(),
               context_map={context_path: context_file_path},
               dir_split=dir_split_number,
               n_file_item=items_per_file,
               default_dir=default_dir)

    r_text = unquote(reference)

    g_add_be = Graph(identifier=base_iri + "be/")
    g_remove_be = Graph(identifier=base_iri + "be/")
    g_add_br = Graph(identifier=base_iri + "br/")
    g_remove_br = Graph(identifier=base_iri + "br/")

    ref_res = rf.retrieve_reference(base_iri + citing, base_iri + cited)
    g_add_be.add((ref_res, GraphEntity.has_content, Literal(r_text)))
    ref_res_text = rf.retrieve_reference_text(ref_res)
    g_remove_be.add((ref_res, GraphEntity.has_content, ref_res_text))

    if accept == "false":
        citing_res = URIRef(base_iri + citing)
        cited_res = URIRef(base_iri + cited)
        cur_time = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%dT%H:%M:%S')
        mod_date = str(rf.retrieve_modification_date(ref_res))

        if cur_time == mod_date: # It didn't exist before
            cur_dir_path, cur_file_path = s.dir_and_file_paths(g_remove_br, base_dir, base_iri)
            cur_g = s.load(cur_file_path)
            for s, p, o in cur_g.triples((cited_res, None, None)):
                if p != RDF.type or o != GraphEntity.expression:
                    g_remove_br.add(s, p, o)

        else: # It exists already
            new_cited = URIRef(str(cp.graph_set().add_br(cp.name, doi_curator, bcite_base_iri)))
            gen_prov_and_store_data(cp, rf, timestamp)
            g_remove_br.add((citing_res, GraphEntity.cites, cited_res))
            g_remove_be.add((ref_res, GraphEntity.references, cited_res))

            g_add_br.add((citing_res, GraphEntity.cites, new_cited))
            g_add_be.add((ref_res, GraphEntity.references, new_cited))

    s.update(g_add_be, g_remove_be, base_dir, base_iri, context_path, temp_dir_for_rdf_loading)
    s.update(g_add_br, g_remove_br, base_dir, base_iri, context_path, temp_dir_for_rdf_loading)
    s.update_all([g_add_br, g_add_be], [g_remove_br, g_remove_be], triplestore_url, base_dir)

    return timestamp, accept, citing, cited, quote(ref_res_text)