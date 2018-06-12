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

from requests.exceptions import ReadTimeout, ConnectTimeout
import json

__author__ = 'essepuntato'

import unicodedata
import re
import os
import shutil
from nltk.metrics import binary_distance as lev
from rdflib import Literal, RDF
from time import sleep
import requests
from urllib.parse import quote
import sys
from netifaces import ifaddresses, AF_INET


def get_ip_id(interface):
    ip = get_ip(interface)
    return ip.split(".")[-1]


def get_ip(interface):
    return ifaddresses(interface)[AF_INET][0]['addr']


def encode_url(u):
    return quote(u, "://")


def dict_get(d, key_list):
    if key_list:
        if type(d) is dict:
            k = key_list[0]
            if k in d:
                return dict_get(d[k], key_list[1:])
            else:
                return None
        elif type(d) is list:
            result = []
            for item in d:
                value = [dict_get(item, key_list)]
                if value is not None:
                    result += value
            return result
        else:
            return None
    else:
        return d


def dict_add(d):
    result = {}
    for k in d:
        value = d[k]
        if value is not None:
            result[k] = value
    return result


def normalise_ascii(string):
    return unicodedata.normalize('NFKD', string).encode("ASCII", "ignore").decode("utf-8")


def normalise_name(name):
    return re.sub("[^A-Za-z ]", "", normalise_ascii(name).lower())


def normalise_id(id_string):
    return re.sub("[^A-Za-z0-9#]", "_", normalise_ascii(id_string).replace("/", "#").lower())


def dict_list_get_by_value_ascii(l, k, v):
    result = []
    v_ascii = normalise_name(v)

    for item in l:
        if type(item) is dict and k in item:
            cur_v = item[k]
            if type(cur_v) is str and normalise_name(cur_v) == v_ascii:
                result += [item]

    return result


def list_from_idx(l, idx_l):
    result = []

    for idx in idx_l:
        result += [l[idx]]

    return result


def string_list_close_match(ls, m):
    final_result = []

    tmp_result = []
    m_ascii = normalise_name(m)
    f_letter = m_ascii[:1]
    for idx, s in enumerate(ls):
        if normalise_name(s)[:1] == f_letter:
            tmp_result += [idx]

    if tmp_result == 1:
        final_result = tmp_result
    elif tmp_result > 1:
        cur_lev = 10000000
        for idx in tmp_result:
            s = ls[idx]
            s_lev = lev(normalise_name(s), m_ascii)
            if s_lev <= cur_lev:
                if s_lev < cur_lev:
                    final_result = []
                final_result += [idx]
                cur_lev = s_lev

    return final_result


def move_file(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
    shutil.move(src, dst)
    return dst + os.sep + os.path.basename(src)


def create_literal(g, res, p, s, dt=None, nor=True):
    string = s
    if not is_string_empty(string):
        g.add((res, p, Literal(string, datatype=dt, normalize=nor)))
        return True
    return False


def create_type(g, res, res_type):
    g.add((res, RDF.type, res_type))


def is_string_empty(string):
    return string is None or string.strip() == ""


def get_short_name(res):
    return re.sub("^.+/([a-z][a-z])(/[0-9]+)?$", "\\1", str(res))


def get_prefix(res):
    return re.sub("^.+/[a-z][a-z]/(0[1-9]+0)?([1-9][0-9]*)$", "\\1", str(res))


def get_count(res):
    return re.sub("^.+/[a-z][a-z]/(0[1-9]+0)?([1-9][0-9]*)$", "\\2", str(res))


def get_data(max_iteration, sec_to_wait, get_url, headers, timeout, repok, reper, is_json=True):
    tentative = 0
    error_no_200 = False
    error_read = False
    error_connection = False
    error_generic = False
    errors = []
    while tentative < max_iteration:
        if tentative != 0:
            sleep(sec_to_wait)
        tentative += 1

        try:
            response = requests.get(get_url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                repok.add_sentence("Data retrieved from '%s'." % get_url)
                if is_json:
                    return json.loads(response.text)
                else:
                    return response.text
            else:
                err_string = "We got an HTTP error when retrieving data (HTTP status code: %s)." % \
                             str(response.status_code)
                if not error_no_200:
                    error_no_200 = True
                if response.status_code == 404:
                    repok.add_sentence(err_string + " However, the process could continue anyway.")
                    # If the resource has not found, we can break the process immediately,
                    # by returning None so as to allow the callee to continue (or not) the process
                    return None
                else:
                    errors += [err_string]
        except ReadTimeout as e:
            if not error_read:
                error_read = True
                errors += ["A timeout error happened when reading results from the API "
                           "when retrieving data. %s" % e]
        except ConnectTimeout as e:
            if not error_connection:
                error_connection = True
                errors += ["A timeout error happened when connecting to the API "
                           "when retrieving data. %s" % e]
        except Exception as e:
            if not error_generic:
                error_generic = True
                errors += ["A generic error happened when trying to use the API "
                           "when retrieving data. %s" % sys.exc_info()[0]]

    # If the process comes here, no valid result has been returned
    reper.add_sentence(" | ".join(errors) + "\n\tRequested URL: " + get_url)


def is_dataset(string_iri):
    return re.search("^.+/[0-9]+$", string_iri) is None


def has_bib_entity_number(subj):
    return re.search("/\d+", str(subj)) is not None


# Variable used in several functions
res_regex = "(.+)/(0[1-9]+0)?([1-9][0-9]*)$"
prov_regex = "(.+)/(0[1-9]+0)?([1-9][0-9]*)(/prov)/(.+)/([0-9]+)$"


def get_resource_number(string_iri):
    cur_number = 0

    if "/prov/" in string_iri:
        if "/pa/" not in string_iri:
            cur_number = int(re.sub(prov_regex, "\\3", string_iri))
    else:
        cur_number = int(re.sub(res_regex, "\\3", string_iri))

    return cur_number


def find_local_line_id(res, n_file_item=1):
    cur_number = get_resource_number(str(res))

    cur_file_split = 0
    while True:
        if cur_number > cur_file_split:
            cur_file_split += n_file_item
        else:
            cur_file_split -= n_file_item
            break

    return cur_number - cur_file_split


def find_paths(string_iri, base_dir, base_iri, default_dir, dir_split, n_file_item):
    """
    This function is responsible for looking for the correct JSON file that contains the data related to the
    resource identified by the variable 'string_iri'. This search takes into account the organisation in
    directories and files, as well as the particular supplier prefix for bibliographic entities, if specified.
    In case no supplier prefix is specified, the 'default_dir' (usually set to "_") is used instead.
    """
    cur_file_path = None

    if is_dataset(string_iri):
        cur_dir_path = (base_dir + re.sub("^%s(.*)$" % base_iri, "\\1", string_iri))[:-1]
        # In case of dataset, the file path is different from regular files, e.g.
        # /corpus/br/index.json
        cur_file_path = cur_dir_path + os.sep + "index.json"
    else:
        cur_number = get_resource_number(string_iri)

        # Find the correct file number where to save the resources
        cur_file_split = 0
        while True:
            if cur_number > cur_file_split:
                cur_file_split += n_file_item
            else:
                break

        # The data have been split in multiple directories and it is not something related
        # with the provenance data of the whole corpus (e.g. provenance agents)
        if dir_split and not string_iri.startswith(base_iri + "prov/"):
            # Find the correct directory number where to save the file
            cur_split = 0
            while True:
                if cur_number > cur_split:
                    cur_split += dir_split
                else:
                    break

            if "/prov/" in string_iri:  # provenance file of a bibliographic entity
                cur_dir_path = base_dir + \
                               re.sub(("^%s" + prov_regex) % base_iri,
                                      ("\\1%s\\2" % os.sep if has_supplier_prefix(string_iri, base_iri) else
                                       "\\1%s%s" % (os.sep, default_dir)), string_iri) + \
                               os.sep + str(cur_split) + os.sep + str(cur_file_split) + os.sep + "prov"
                # In case of provenance, the file path is different from regular files, e.g.
                # /corpus/br/10000/1000/prov/se.json
                cur_file_path = cur_dir_path + os.sep + re.sub(
                    ("^%s" + prov_regex) % base_iri, "\\5", string_iri) + ".json"
            else:  # regular bibliographic entity
                cur_dir_path = base_dir + \
                               re.sub(("^%s" + res_regex) % base_iri,
                                      ("\\1%s\\2" % os.sep if has_supplier_prefix(string_iri, base_iri) else
                                       "\\1%s%s" % (os.sep, default_dir)),
                                      string_iri) + \
                               os.sep + str(cur_split)

                cur_file_path = cur_dir_path + os.sep + str(cur_file_split) + ".json"
        # Enter here if no split is needed
        elif dir_split == 0:
            if "/prov/" in string_iri:
                cur_dir_path = base_dir + \
                               re.sub(("^%s" + prov_regex) % base_iri,
                                      ("\\1%s\\2" % os.sep if has_supplier_prefix(string_iri, base_iri) else
                                       "\\1%s%s" % (os.sep, default_dir)), string_iri) + \
                               os.sep + str(cur_file_split) + os.sep + "prov"
                cur_file_path = cur_dir_path + os.sep + re.sub(
                    ("^%s" + prov_regex) % base_iri, "\\5", string_iri) + ".json"
            else:
                cur_dir_path = base_dir + \
                               re.sub(("^%s" + res_regex) % base_iri,
                                      ("\\1%s\\2" % os.sep if has_supplier_prefix(string_iri, base_iri) else
                                       "\\1%s%s" % (os.sep, default_dir)),
                                      string_iri)

                cur_file_path = cur_dir_path + os.sep + str(cur_file_split) + ".json"
        # Enter here if the data is about a provenance agent, e.g.,
        # /corpus/prov/
        else:
            cur_dir_path = base_dir + re.sub(("^%s" + res_regex) % base_iri, "\\1", string_iri)
            cur_file_path = cur_dir_path + os.sep + re.sub(res_regex, "\\2\\3", string_iri) + ".json"

    return cur_dir_path, cur_file_path


def has_supplier_prefix(string_iri, base_iri):
    return re.search("^%s[a-z][a-z]/0" % base_iri, string_iri) is not None
