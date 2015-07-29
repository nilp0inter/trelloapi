#!/usr/bin/env python
"""
Translate the documentation of Trello API into a YAML structure with all
the information needed by the api module.

"""
from base64 import b64encode
from collections import defaultdict
from lxml import html
from pprint import pprint
import gzip
import re

from html2text import html2text
from lxml import etree
import requests
import yaml

TRELLO_API_DOC = 'https://trello.com/docs/api/'
HTTP_METHODS = {'OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE',
                'TRACE', 'CONNECT'}
EP_DESC_REGEX = re.compile(
    '.*({methods})\s([\/a-zA-Z0-9\[\]\s_]+).*'.format(
        methods='|'.join(HTTP_METHODS)))

def _is_url_arg(p):
    """
    Is an argument of the URL.

    >>> _is_url_arg('[idAction]')
    True
    >>> _is_url_arg('actions')
    False

    """
    return p.startswith('[')


def _is_api_definition(line):
    """
    Is a definition of a Trello endpoint.

    >>> _is_api_definition('GET /1/actions/[idAction]')
    True
    >>> _is_api_definition('action')
    False

    """
    return line.split(' ', 1)[0] in HTTP_METHODS


def _camelcase_to_underscore(url):
    """
    Translate camelCase into underscore format.

    >>> _camelcase_to_underscore('minutesBetweenSummaries')
    'minutes_between_summaries'

    """
    def upper2underscore(text):
        for char in text:
            if char.islower():
                yield char
            else:
                yield '_'
                if char.isalpha():
                    yield char.lower()
    return ''.join(upper2underscore(url))


def create_tree(endpoints):
    """
    Creates the Trello endpoint tree.

    >>> r = {'1': { \
                 'actions': {'METHODS': {'GET'}}, \
                 'boards': { \
                     'members': {'METHODS': {'DELETE'}}}} \
            }
    >>> r == create_tree([ \
                 'GET /1/actions/[idAction]', \
                 'DELETE /1/boards/[board_id]/members/[idMember]'])
    True

    """
    tree = {}

    for method, url, doc in endpoints:
        path = [p for p in url.strip('/').split('/')]
        here = tree

        # First element (API Version).
        version = path[0]
        here.setdefault(version, {})
        here = here[version]

        # The rest of elements of the URL.
        for p in path[1:]:
            part = _camelcase_to_underscore(p)
            here.setdefault(part, {})
            here = here[part]

        # Allowed HTTP methods.
        if not 'METHODS' in here:
            here['METHODS'] = [[method, doc]]
        else:
            if not method in here['METHODS']:
                here['METHODS'].append([method, doc])

    return tree


def main():
    """
    Prints the complete YAML.

    """
    ep = requests.get(TRELLO_API_DOC).content
    root = html.fromstring(ep)

    links = root.xpath('//a[contains(@class, "reference internal")]/@href')
    pages = [requests.get(TRELLO_API_DOC + u)
             for u in links if u.endswith('index.html')]

    endpoints = []
    for page in pages:
        root = html.fromstring(page.content)
        sections = root.xpath('//div[@class="section"]/h2/..')
        for sec in sections:
            ep_html = etree.tostring(sec).decode('utf-8')
            ep_text = html2text(ep_html).splitlines()
            match = EP_DESC_REGEX.match(ep_text[0])
            if not match:
                continue
            ep_method, ep_url = match.groups()
            ep_text[0] = ' '.join([ep_method, ep_url])
            ep_doc = b64encode(gzip.compress('\n'.join(ep_text).encode('utf-8')))
            endpoints.append((ep_method, ep_url, ep_doc))

    print(yaml.dump(create_tree(endpoints)))


if __name__ == '__main__':
    main()
