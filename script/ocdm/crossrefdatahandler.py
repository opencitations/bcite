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

from script.support.support import dict_list_get_by_value_ascii as dgt
from script.support.support import string_list_close_match as slc
from script.support.support import dict_get as dg
from script.ocdm.graphlib import GraphSet
from script.ocdm.graphlib import GraphEntity
from re import sub


class CrossrefDataHandler(object):
    isbn_base_url = "http://id.crossref.org/isbn/"
    member_base_url = "http://id.crossref.org/member/"

    isbn_types = [
        "book", "book-set", "dissertation", "edited-book",
        "monograph", "proceedings", "reference-book"
    ]

    issn_types = ["book-series", "book-set", "journal", "report-series", "standard-series"]

    def __init__(self, graph_set=GraphSet("http://localhost:8000/corpus/", "corpus/context.json",
                                          "test/share/id-counter/_/", 1000, ""),
                 orcid_finder=None, resource_finder=None):
        self.name = "Crossref Data Handler"
        self.id = "Crossref"
        self.of = orcid_finder
        self.rf = resource_finder
        self.g_set = graph_set

    def __associate_isbn(self, res, json, source):
        for string in CrossrefDataHandler.get_all_isbns(json):
            cur_id = self.g_set.add_id(self.name, self.id, source)
            if cur_id.create_isbn(string):
                res.has_id(cur_id)

    def __get_ids_for_container(self, json):
        result = {}

        if "container-title" in json and len(json["container-title"]) > 0:
            cur_issns = CrossrefDataHandler.get_all_issns(json)
            if cur_issns:
                result[GraphEntity.issn] = cur_issns

            cur_isbns = CrossrefDataHandler.get_all_isbns(json)
            if cur_isbns:
                result[GraphEntity.isbn] = cur_isbns

        return result

    def __associate_issn(self, res, json, source):
        for string in CrossrefDataHandler.get_all_issns(json):
            cur_id = self.g_set.add_id(self.name, self.id, source)
            if cur_id.create_issn(string):
                res.has_id(cur_id)

    @staticmethod
    def create_title_from_list(title_list):
        cur_title = ""

        for title in title_list:
            strip_title = title.strip()
            if strip_title != "":
                if cur_title == "":
                    cur_title = strip_title
                else:
                    cur_title += " - " + strip_title

        return cur_title

    @staticmethod
    def add_journal_data(j, title):
        j.create_journal()
        j.create_title(title)

    @staticmethod
    def add_volume_data(vol, num):
        vol.create_volume()
        vol.create_number(num)

    @staticmethod
    def get_ids_for_type(json):
        result = {}

        if "DOI" in json:
            result[GraphEntity.doi] = [json["DOI"]]

        if "URL" in json:
            result[GraphEntity.url] = [json["URL"]]

        if "container-title" not in json or len(json["container-title"]) == 0:
            cur_issns = CrossrefDataHandler.get_all_issns(json)
            if cur_issns:
                result[GraphEntity.issn] = cur_issns

            cur_isbns = CrossrefDataHandler.get_all_isbns(json)
            if cur_isbns:
                result[GraphEntity.isbn] = cur_isbns

        return result

    @staticmethod
    def get_all_issns(json):
        result = []
        if "ISSN" in json:
            for string in json["ISSN"]:
                if string != "0000-0000":
                    result += [string]
        return result

    @staticmethod
    def get_all_isbns(json):
        result = []
        if "ISBN" in json:
            for string in json["ISBN"]:
                result += [sub("^" + CrossrefDataHandler.isbn_base_url, "", string)]
        return result

    def title(self, cur_br, key, json, *args):
        cur_title = CrossrefDataHandler.create_title_from_list(json[key])
        cur_br.create_title(cur_title)

    def subtitle(self, cur_br, key, json, *args):
        cur_br.create_subtitle(CrossrefDataHandler.create_title_from_list(json[key]))

    def author(self, cur_br, key, json, source, *args):
        # Get all ORCID of the authors (if any)
        all_authors = json[key]
        all_family_names = dg(all_authors, ["family"])
        author_orcid = []
        if "DOI" in json and all_family_names:
            doi_string = json["DOI"]
            if self.of is not None:
                author_orcid = self.of.get_orcid_ids(doi_string, all_family_names)

        # Used to create ordered list of authors/editors of bibliographic entities
        prev_role = None

        # Analyse all authors
        for author in json["author"]:
            given_name_string = None
            if "given" in author:
                given_name_string = author["given"]
            family_name_string = None
            if "family" in author:
                family_name_string = author["family"]

            cur_orcid_record = None  # TODO: handle if ORCID in Crossref
            if family_name_string:
                # Get all the ORCID/author records retrieved that share the
                # family name into consideration
                orcid_with_such_family = dgt(author_orcid, "family", family_name_string)
                author_with_such_family = dgt(all_authors, "family", family_name_string)
                if len(orcid_with_such_family) == 1 and len(author_with_such_family) == 1:
                    cur_orcid_record = orcid_with_such_family[0]
                elif given_name_string is not None and \
                        len(orcid_with_such_family) >= 1 and len(author_with_such_family) >= 1:
                    # From the previous lists of ORCID/author record, get the list
                    # of all the given name defined
                    orcid_given_with_such_family = dg(orcid_with_such_family, ["given"])
                    author_given_with_such_family = dg(author_with_such_family, ["given"])

                    # Get the indexes of the previous list that best match with the
                    # given name of the author we are considering
                    closest_orcid_matches_idx = \
                        slc(orcid_given_with_such_family, given_name_string)
                    closest_author_matches_idx = \
                        slc(author_given_with_such_family, given_name_string)
                    if len(closest_orcid_matches_idx) == 1 and \
                            len(closest_author_matches_idx) == 1:
                        closest_author_orcid_matches_idx = slc(
                            author_given_with_such_family, orcid_given_with_such_family[0])
                        if closest_author_orcid_matches_idx == closest_author_matches_idx:
                            cur_orcid_record = \
                                orcid_with_such_family[closest_orcid_matches_idx[0]]

            # An ORCID has been found to match with such author record, and we try to
            # see if such orcid (and thus, the author) has been already added in the
            # store
            retrieved_agent = None
            if cur_orcid_record is not None and self.rf is not None:  # TODO: handle if ORCID in Crossref
                retrieved_agent = self.rf.retrieve_from_orcid(cur_orcid_record["orcid"])

            # If the resource does not exist already, create a new one
            if retrieved_agent is None:
                cur_agent = self.g_set.add_ra(self.name, self.id, source)
                if cur_orcid_record is not None and self.of is not None:
                    cur_agent_orcid = \
                        self.g_set.add_id(self.of.name, self.of.id, self.of.get_last_query())
                    cur_agent_orcid.create_orcid(cur_orcid_record["orcid"])
                    cur_agent.has_id(cur_agent_orcid)

                if given_name_string is not None:
                    cur_agent.create_given_name(given_name_string)
                elif cur_orcid_record is not None and "given" in cur_orcid_record:
                    cur_agent.create_given_name(cur_orcid_record["given"])

                if family_name_string is not None:
                    cur_agent.create_family_name(family_name_string)
                elif cur_orcid_record is not None and "family" in cur_orcid_record:
                    cur_agent.create_family_name(cur_orcid_record["family"])
            else:
                cur_agent = self.g_set.add_ra(
                    self.name, self.id, source, retrieved_agent)

            # Add statements related to the author resource (that could or could not
            # exist in the store)
            cur_role = self.g_set.add_ar(self.name, self.id, source)
            if json["type"] == "edited-book":
                cur_role.create_editor(cur_br)
            else:
                cur_role.create_author(cur_br)
            cur_agent.has_role(cur_role)

            if prev_role is not None:
                cur_role.follows(prev_role)

            prev_role = cur_role

    def publisher(self, cur_br, key, json, source, *args):
        cur_agent = None

        # Check if the publishier already exists
        if "member" in json and json["member"] is not None:
            cur_member_url = json["member"]
            retrieved_agent = None
            if self.rf is not None:
                retrieved_agent = self.rf.retrieve_from_url(cur_member_url)  # TODO: retrieve also by name and by list name
            if retrieved_agent is not None:
                cur_agent = self.g_set.add_ra(
                    self.name, self.id, source, retrieved_agent)
        else:
            cur_member_url = None

        # If the publisher is not already defined in the knowledge base,
        # create a new one.
        if cur_agent is None:
            cur_agent = self.g_set.add_ra(self.name, self.id, source)
            cur_agent.create_name(json[key])

            if cur_member_url is not None:
                cur_agent_id = self.g_set.add_id(self.name, self.id, source)
                cur_agent_id.create_url(json["member"])
                cur_agent.has_id(cur_agent_id)

        cur_role = self.g_set.add_ar(self.name, self.id, source)
        cur_role.create_publisher(cur_br)
        cur_agent.has_role(cur_role)

    def doi(self, cur_br, key, json, source, doi_curator, doi_source_provider, doi_source, *args):
        cur_id = self.g_set.add_id(doi_curator, doi_source_provider, doi_source)
        if cur_id.create_doi(json[key]):
            cur_br.has_id(cur_id)

    def issued(self, cur_br, key, json, *args):
        cur_br.create_pub_date(json[key]["date-parts"][0])

    def url(self, cur_br, key, json, source, *args):
        cur_id = self.g_set.add_id(self.name, self.id, source)
        if cur_id.create_url(json[key]):
            cur_br.has_id(cur_id)

    def page(self, cur_br, key, json, source, *args):
        cur_page = json[key]
        cur_re = self.g_set.add_re(self.name, self.id, source)
        if cur_re.create_starting_page(cur_page):
            cur_re.create_ending_page(cur_page)
            cur_br.has_format(cur_re)

    def container_title(self, cur_br, key, json, source, *args):
        retrieved_container = None
        cont_br = None
        cur_type = json["type"]

        container_ids = self.__get_ids_for_container(json)
        cur_issue_id = json["issue"] if "issue" in json else None
        cur_volume_id = json["volume"] if "volume" in json else None

        retrieved_container = None
        if self.rf is not None:
            if cur_type == "journal-article":
                if cur_issue_id is None:
                    if cur_volume_id is None:
                        retrieved_container = self.rf.retrieve(container_ids)
                    else:
                        retrieved_container = \
                            self.rf.retrieve_volume_from_journal(container_ids, cur_volume_id)
                else:
                    retrieved_container = self.rf.retrieve_issue_from_journal(
                        container_ids, cur_issue_id, cur_volume_id)
            elif cur_type == "journal-issue":
                if cur_volume_id is None:
                    retrieved_container = self.rf.retrieve(container_ids)
                else:
                    retrieved_container = \
                        self.rf.retrieve_volume_from_journal(container_ids, cur_volume_id)
            else:
                retrieved_container = self.rf.retrieve(container_ids)

        if retrieved_container is not None:
            cont_br = self.g_set.add_br(
                self.name, self.id, source, retrieved_container)
        else:
            cur_container_title = None
            if len(json[key]) > 0:
                cur_container_title = CrossrefDataHandler.create_title_from_list(json[key])

            if cur_container_title is not None:
                cur_container_type = None
                cont_br = self.g_set.add_br(self.name, self.id, source)

                if cur_type == "book-chapter":
                    cur_container_type = "book"
                    cont_br.create_book()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "book-part":
                    cur_container_type = "book"
                    cont_br.create_book()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "book-section":
                    cur_container_type = "book"
                    cont_br.create_book()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "book-track":
                    cur_container_type = "book-section"
                    cont_book = self.g_set.add_br(self.name, self.id, source)
                    cont_book.create_book()
                    cont_book.create_title(cur_container_title)
                    self.__associate_isbn(cont_book, json, source)
                    cont_book.has_part(cont_br)
                    cont_br.create_book_section()
                elif cur_type == "component":
                    cur_container_type = "component"
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "dataset":
                    cur_container_type = "dataset"
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "journal-article":
                    if "issue" not in json and "volume" not in json:
                        cur_container_type = "journal"
                        jou_br = cont_br
                        CrossrefDataHandler.add_journal_data(jou_br, cur_container_title)
                    else:
                        # If we have an issue or a volume specified, the journal may have
                        # been already added to the corpus in the past. Thus, check it
                        # before creating a new object for that journal
                        retrieved_journal = None
                        if self.rf is not None:
                            retrieved_journal = self.rf.retrieve(container_ids)
                        if retrieved_journal is None:
                            jou_br = self.g_set.add_br(self.name, self.id, source)
                            self.__associate_issn(jou_br, json, source)
                            CrossrefDataHandler.add_journal_data(
                                jou_br, cur_container_title)
                        else:
                            jou_br = self.g_set.add_br(
                                self.name, self.id, source, retrieved_journal)

                        if "issue" in json:
                            cur_container_type = "issue"
                            cont_br.create_issue()
                            cont_br.create_number(json["issue"])
                            if "volume" not in json:
                                jou_br.has_part(cont_br)

                        if "volume" in json:
                            cur_volume_id = json["volume"]
                            if "issue" in json:
                                # If we have an issue specified, the volume may have
                                # been already added to the corpus in the past. Thus, check it
                                # before creating a new object for that volume
                                retrieved_volume = None
                                if self.rf is not None:
                                    retrieved_volume = self.rf.retrieve_volume_from_journal(
                                        container_ids, cur_volume_id)
                                if retrieved_volume is None:
                                    vol_br = self.g_set.add_br(
                                        self.name, self.id, source)
                                    CrossrefDataHandler.add_volume_data(vol_br, cur_volume_id)
                                    jou_br.has_part(vol_br)
                                else:
                                    vol_br = self.g_set.add_br(
                                        self.name, self.id, source, retrieved_volume)
                                vol_br.has_part(cont_br)
                            else:
                                cur_container_type = "volume"
                                vol_br = cont_br
                                CrossrefDataHandler.add_volume_data(vol_br, cur_volume_id)
                                jou_br.has_part(vol_br)
                elif cur_type == "journal-issue":
                    cur_container_type = "journal"
                    if "volume" in json:
                        cur_container_type = "volume"
                        CrossrefDataHandler.add_volume_data(cont_br, json["volume"])
                        # If we have a volume specified, the journal may have
                        # been already added to the corpus in the past. Thus, check it
                        # before creating a new object for that journal
                        retrieved_journal = None
                        if self.rf is not None:
                            retrieved_journal = self.rf.retrieve(container_ids)
                        if retrieved_journal is None:
                            jou_br = self.g_set.add_br(self.name, self.id, source)
                            self.__associate_issn(jou_br, json, source)
                            CrossrefDataHandler.add_journal_data(
                                jou_br, cur_container_title)
                        else:
                            jou_br = self.g_set.add_br(
                                self.name, self.id, source, retrieved_journal)

                        jou_br.has_part(cont_br)
                    else:
                        jou_br = cont_br
                        CrossrefDataHandler.add_journal_data(jou_br, cur_container_title)

                elif cur_type == "journal-volume":
                    cur_container_type = "volume"
                    CrossrefDataHandler.add_journal_data(cont_br, cur_container_title)
                    self.__associate_issn(cont_br, json, source)
                elif cur_type == "other":
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "proceedings-article":
                    cur_container_type = "proceedings"
                    cont_br.create_proceedings()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "reference-entry":
                    cur_container_type = "reference-book"
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "report":
                    cur_container_type = "report-series"
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)
                elif cur_type == "standard":
                    cur_container_type = "standard-series"
                    cont_br.create_expression_collection()
                    cont_br.create_title(cur_container_title)

                # If the current type is in any of the ISSN or ISBN list
                # add the identifier to the resource
                if cur_container_type is not None:
                    if cur_container_type in CrossrefDataHandler.issn_types:
                        self.__associate_issn(cont_br, json, source)
                    if cur_container_type in CrossrefDataHandler.isbn_types:
                        self.__associate_isbn(cont_br, json, source)

        if cont_br is not None:
            cont_br.has_part(cur_br)

    def type(self, cur_br, key, json, source, *args):
        cur_type = json[key]
        if cur_type == "book":
            cur_br.create_book()
        elif cur_type == "book-chapter":
            cur_br.create_book_chapter()
        elif cur_type == "book-part":
            cur_br.create_book_part()
        elif cur_type == "book-section":
            cur_br.create_book_section()
        elif cur_type == "book-series":
            cur_br.create_book_series()
        elif cur_type == "book-set":
            cur_br.create_book_set()
        elif cur_type == "book-track":
            cur_br.create_book_track()
        elif cur_type == "component":
            cur_br.create_component()
        elif cur_type == "dataset":
            cur_br.create_dataset()
        elif cur_type == "dissertation":
            cur_br.create_dissertation()
        elif cur_type == "edited-book":
            cur_br.create_edited_book()
        elif cur_type == "journal":
            CrossrefDataHandler.add_journal_data(cur_br, CrossrefDataHandler.create_title_from_list(json["title"]))
        elif cur_type == "journal-article":
            cur_br.create_journal_article()
        elif cur_type == "journal-issue":
            cur_br.create_issue()
        elif cur_type == "journal-volume":
            cur_br.create_volume()
        elif cur_type == "monograph":
            cur_br.create_monograph()
        elif cur_type == "other":
            cur_br.create_other()
        elif cur_type == "proceedings":
            cur_br.create_proceedings()
        elif cur_type == "proceedings-article":
            cur_br.create_proceedings_article()
        elif cur_type == "reference-book":
            cur_br.create_reference_book()
        elif cur_type == "reference-entry":
            cur_br.create_reference_entry()
        elif cur_type == "report":
            cur_br.create_report()
        elif cur_type == "report-series":
            cur_br.create_report_series()
        elif cur_type == "standard":
            cur_br.create_standard()
        elif cur_type == "standard-series":
            cur_br.create_standard_series()

        # If the current type is in any of the ISSN or ISBN list
        # add the identifier to the resource
        if cur_type in CrossrefDataHandler.issn_types:
            self.__associate_issn(cur_br, json, source)
        if cur_type in CrossrefDataHandler.isbn_types:
            self.__associate_isbn(cur_br, json, source)

    def process_json(self, json, source, doi_curator=None, doi_source_provider=None, doi_source=None):
        cur_br = self.g_set.add_br(self.name, self.id, source)
        for key in json:
            l_key = key.lower().replace("-", "_")
            try:
                getattr(self, l_key)(cur_br, key, json, source, doi_curator, doi_source_provider, doi_source)  # TODO: say what it does

            except AttributeError:
                pass  # do nothing

        return cur_br
