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

from script.ocdm.graphlib import GraphEntity as ge
from script.support.support import dict_get as dg
from script.support.support import get_data
from script.support.support import encode_url
from script.spacin.formatproc import FormatProcessor
from script.ocdm.crossrefdatahandler import CrossrefDataHandler
from script.ocdm.graphlib import GraphEntity
from re import sub


class CrossrefProcessor(FormatProcessor):
    def __init__(self,
                 base_iri,
                 context_base,
                 info_dir,
                 entries,
                 res_finder,
                 of_finder,
                 n_file_item,
                 supplier_prefix,
                 headers={"User-Agent": "SPACIN / CrossrefProcessor (via OpenCitations - "
                                        "http://opencitations.net; mailto:contact@opencitations.net)"},
                 sec_to_wait=10,
                 max_iteration=6,
                 timeout=30,
                 use_doi_in_bibentry_as_id=True,
                 use_url_in_bibentry_as_id=True,
                 crossref_min_similarity_score=75.0):
        self.crossref_api_works = "https://api.crossref.org/works/"
        self.crossref_api_search = "https://api.crossref.org/works?rows=1&query="
        self.headers = headers
        self.sec_to_wait = sec_to_wait
        self.max_iteration = max_iteration
        self.timeout = timeout
        self.rf = res_finder
        self.of = of_finder
        self.get_bib_entry_url = use_url_in_bibentry_as_id
        self.get_bib_entry_doi = use_doi_in_bibentry_as_id
        self.crossref_min_similarity_score = crossref_min_similarity_score
        super(CrossrefProcessor, self).__init__(
            base_iri, context_base, info_dir, entries, n_file_item, supplier_prefix, "Crossref")

    def __process_entity(self, entity, api_url):
        return get_data(self.max_iteration, self.sec_to_wait, api_url + entity,
                        self.headers, self.timeout, self.repok, self.reperr)

    def process_entry(self, entry):
        entry_cleaned = FormatProcessor.clean_entry(entry)
        cur_json = self.get_crossref_item(
            self.__process_entity(entry_cleaned, self.crossref_api_search))
        if cur_json is not None:
            return self.process_crossref_json(
                cur_json, self.crossref_api_search + entry_cleaned,
                self.name, self.id, self.source)

    def process_doi(self, doi, doi_curator, doi_source_provider):
        existing_res = self.rf.retrieve_from_doi(doi)
        if existing_res is None:
            cur_json = self.get_crossref_item(self.__process_entity(doi, self.crossref_api_works))
            if cur_json is not None:
                return self.process_crossref_json(
                    cur_json, self.crossref_api_works + encode_url(doi), doi_curator,
                    doi_source_provider, self.source)
        else:
            return self.process_existing_by_id(existing_res, self.id)

    def process_pmid(self, pmid):
        existing_res = self.rf.retrieve_from_pmid(pmid)
        return self.process_existing_by_id(existing_res, self.id)

    def process_pmcid(self, pmcid):
        existing_res = self.rf.retrieve_from_pmcid(pmcid)
        return self.process_existing_by_id(existing_res, self.id)

    def process_url(self, url):
        existing_res = self.rf.retrieve_from_url(url)
        return self.process_existing_by_id(existing_res, self.id)

    def process_existing_by_id(self, existing_res, source_provider):
        if existing_res is not None:
            result = self.g_set.add_br(self.name, source_provider, self.source, existing_res)
            self.rf.update_graph_set(self.g_set)
            return result

    def process_citing_entity(self):
        citing_entity = None

        if self.occ is not None:
            citing_resource = self.rf.retrieve_entity(self.occ, GraphEntity.expression)
            citing_entity = self.g_set.add_br(self.name, self.id, self.source_provider, citing_resource)
        if citing_entity is None and self.doi is not None:
            citing_entity = self.process_doi(self.doi, self.curator, self.source_provider)

        if citing_entity is None:
            citing_entity = self.g_set.add_br(self.name)
            self.__add_doi(citing_entity, self.doi, self.curator)
            self.rf.update_graph_set(self.g_set)
            self.repok.add_sentence(
                self.message("The citing entity has been created even if no results have "
                             "been returned by the API.",
                             "doi", self.doi))

        # Add other ids if they exist
        self.__add_pmid(citing_entity, self.pmid)
        self.__add_pmcid(citing_entity, self.pmcid)

        cited_entities = self.process_references()

        if cited_entities is not None:
            for idx, cited_entity in enumerate(cited_entities):
                citing_entity.has_citation(cited_entity)
                cur_bibentry = dg(self.entries[idx], ["bibentry"])
                if cur_bibentry is not None and cur_bibentry.strip():
                    cur_be = self.g_set.add_be(self.curator, self.source_provider, self.source)
                    citing_entity.contains_in_reference_list(cur_be)
                    cited_entity.has_reference(cur_be)
                    cur_be.create_content(cur_bibentry.strip())

            return self.g_set

    def process(self):
        """This methods returns a GraphSet populated with the citation data form the input
        source, or None if any issue has been encountered."""
        if self.doi is not None:
            citing_resource = self.rf.retrieve_citing_from_doi(self.doi)
            if citing_resource is None and self.pmid is not None:
                citing_resource = self.rf.retrieve_citing_from_pmid(self.pmid)
            if citing_resource is None and self.pmcid is not None:
                citing_resource = self.rf.retrieve_citing_from_pmcid(self.pmcid)
            if citing_resource is None and self.url is not None:
                citing_resource = self.rf.retrieve_citing_from_url(self.url)

            if citing_resource is None:
                return self.process_citing_entity()
            else:
                self.repok.add_sentence(
                    "The citing entity with DOI '%s' has been already "
                    "processed in the past." % self.doi)
        else:  # No DOI has been specified for the citing resource
            self.reperr.add_sentence("No DOI has been specified for the citing resource.")

    def process_references(self):
        result = []

        for full_entry in self.entries:
            self.repok.new_article()
            self.reperr.new_article()
            cur_res = None

            entry = dg(full_entry, ["bibentry"])
            do_process_entry = True
            process_string = dg(full_entry, ["process_entry"])
            if process_string is not None:
                do_process_entry = process_string.lower().strip() == "true"
            provided_doi = dg(full_entry, ["doi"])
            provided_pmid = dg(full_entry, ["pmid"])
            provided_pmcid = dg(full_entry, ["pmcid"])
            provided_url = dg(full_entry, ["url"])

            # This is useful if additional data are stored in the field URL, e.g.:
            # 'http://pub.stat.ee/px/web.2001/dialog/statfile1.asp. Accessed on 2009'
            if provided_url is not None:
                provided_url = FormatProcessor.extract_url(provided_url)

            extracted_doi = FormatProcessor.extract_doi(entry)
            extracted_doi_used = False
            extracted_url = FormatProcessor.extract_url(entry)

            if provided_doi is not None:
                cur_res = self.process_doi(provided_doi, self.curator, self.source_provider)
                if cur_res is not None:
                    self.repok.add_sentence(
                        self.message("The entity has been found by means of the "
                                     "DOI provided as input by %s." % self.source_provider,
                                     "DOI", provided_doi))

            if cur_res is None and provided_pmid is not None:
                cur_res = self.process_pmid(provided_pmid)
                if cur_res is not None:
                    self.repok.add_sentence(
                        self.message("The entity has been found by means of the "
                                     "PMID provided as input by %s." % self.source_provider,
                                     "PMID", provided_pmid))

            if cur_res is None and provided_pmcid is not None:
                cur_res = self.process_pmcid(provided_pmcid)
                if cur_res is not None:
                    self.repok.add_sentence(
                        self.message("The entity has been found by means of the "
                                     "PMCID provided as input by %s." % self.source_provider,
                                     "PMCID", provided_pmcid))

            if cur_res is None and provided_url is not None:
                cur_res = self.process_url(provided_url)
                if cur_res is not None:
                    self.repok.add_sentence(
                        self.message("The entity has been found by means of the "
                                     "URL provided as input by %s." % self.source_provider,
                                     "URL", provided_url))

            if cur_res is None and entry is not None:
                if do_process_entry:
                    cur_res = self.process_entry(entry)

                if cur_res is None:
                    if self.get_bib_entry_doi and extracted_doi is not None:
                        extracted_doi_used = True
                        cur_res = self.process_doi(extracted_doi, self.name, self.source_provider)
                        if cur_res is not None:
                            self.repok.add_sentence(
                                self.message("The entity for '%s' has been found by means of the "
                                             "DOI extracted from it." % entry,
                                             "DOI", extracted_doi))
                    if cur_res is None and self.get_bib_entry_url and extracted_url is not None:
                        existing_res = self.rf.retrieve_from_url(extracted_url)
                        if existing_res is not None:
                            cur_res = self.g_set.add_br(
                                self.name, self.source_provider, self.source, existing_res)
                            self.repok.add_sentence(
                                self.message("The entity for '%s' has been found by means of the "
                                             "URL extracted from it." % entry,
                                             "URL", extracted_url))

                else:
                    self.repok.add_sentence(
                        self.message(
                            "The entity has been retrieved by using the search API.",
                            "entry", entry))

            # If no errors were generated, proceed
            if self.reperr.is_empty():
                # If it is none
                if cur_res is None:
                    cur_res = self.g_set.add_br(self.name)
                    self.rf.update_graph_set(self.g_set)
                    self.repok.add_sentence(
                        self.message("The entity has been created even if no results have "
                                     "been returned by the API.",
                                     "entry", entry))

                # Add the DOI, the PMID and the PMCID if they have been provided by the curator
                # (if they are not already associated to the resource)
                self.__add_doi(cur_res, provided_doi, self.curator)
                self.__add_pmid(cur_res, provided_pmid)
                self.__add_pmcid(cur_res, provided_pmcid)
                self.__add_url(cur_res, provided_url)

                # Add any DOI extracted from the entry if it is not already included (and only if
                # a resource has not been retrieved by a DOI specified in the entry explicitly, or
                # by a Crossref search.
                if self.get_bib_entry_doi and extracted_doi_used:
                    self.__add_doi(cur_res, extracted_doi, self.name)

                # Add any URL extracted from the entry if it is not already included
                if self.get_bib_entry_url:
                    self.__add_url(cur_res, extracted_url)

                result += [cur_res]
                self.rf.update_graph_set(self.g_set)

            else:  # If errors have been raised, stop the process for this entry (by returning None)
                return None

        # If the process comes here, then everything worked correctly
        return result

    def __add_url(self, cur_res, extracted_url):
        self.rf.update_graph_set(self.g_set)
        if extracted_url is not None:
            cur_id = self.rf.retrieve_br_url(cur_res.res, extracted_url)

            if cur_id is None:
                cur_id = self.g_set.add_id(self.name, self.source_provider, self.source)
                cur_id.create_url(extracted_url)
                cur_res.has_id(cur_id)

    def __add_pmid(self, cur_res, pmid_string):
        self.rf.update_graph_set(self.g_set)
        if pmid_string is not None:
            cur_id = self.rf.retrieve_br_pmid(cur_res.res, pmid_string)

            if cur_id is None:
                cur_id = self.g_set.add_id(self.curator, self.source_provider, self.source)
                cur_id.create_pmid(pmid_string)
                cur_res.has_id(cur_id)

    def __add_pmcid(self, cur_res, pmcid_string):
        self.rf.update_graph_set(self.g_set)
        if pmcid_string is not None:
            cur_id = self.rf.retrieve_br_pmcid(cur_res.res, pmcid_string)

            if cur_id is None:
                cur_id = self.g_set.add_id(self.curator, self.source_provider, self.source)
                cur_id.create_pmcid(pmcid_string)
                cur_res.has_id(cur_id)

    def __add_doi(self, cur_res, extracted_doi, curator):
        self.rf.update_graph_set(self.g_set)
        if extracted_doi is not None:
            cur_id = self.rf.retrieve_br_doi(cur_res.res, extracted_doi)

            if cur_id is None:
                cur_id = self.g_set.add_id(curator, self.source_provider, self.source)
                cur_id.create_doi(extracted_doi)
                cur_res.has_id(cur_id)

    def get_crossref_item(self, json_crossref):
        result = None
        if json_crossref is not None and json_crossref["status"] == "ok":
            if json_crossref["message-type"] in ["work", "member"]:
                result = json_crossref["message"]
            elif json_crossref["message-type"] == "work-list":
                result = json_crossref["message"]["items"][0]
                if result["score"] < self.crossref_min_similarity_score:
                    result = None
        return result

    def process_crossref_json(
            self, crossref_json, crossref_source,
            doi_curator=None, doi_source_provider=None, doi_source=None):
        # Check if the found bibliographic resource already exist either
        # in the triplestore or in the current graph set.
        self.rf.update_graph_set(self.g_set)
        retrieved_resource = self.rf.retrieve(CrossrefDataHandler.get_ids_for_type(crossref_json))

        if retrieved_resource is not None:
            cur_br = self.g_set.add_br(self.name, self.id, crossref_source, retrieved_resource)
        else:
            cdh = CrossrefDataHandler(graph_set=self.g_set, orcid_finder=self.of, resource_finder=self.rf)
            cur_br = cdh.process_json(crossref_json, crossref_source, doi_curator, doi_source_provider, doi_source)

        return cur_br

    def message(self, mess, entity_type, entity, url="not provided"):
        return super(CrossrefProcessor, self).message(mess) + \
               "\n\t%s: %s\n\tURL: %s" % (entity_type, entity, url)


