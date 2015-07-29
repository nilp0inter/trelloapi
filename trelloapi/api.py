#!/usr/bin/env python
"""
Trello API.

"""
from functools import partial
import os
import gzip
from base64 import b64decode

import requests
import yaml

__all__ = []

TRELLO_URL = 'https://trello.com/'
HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, 'endpoints.yaml'), 'rb') as ep_file:
    ENDPOINTS = yaml.load(ep_file.read())



class TrelloAPI:
    """
    Interface with Trello API.

    Dynamically generates methods corresponding with API URLs.

    """
    def __init__(self, endpoints, name, apikey, parent=None, api_arg=None):
        self._endpoints = endpoints
        self._name = name
        self._apikey = apikey
        self._parent = parent
        self._api_arg = api_arg

        self._allowed_args = []

        for name, content in self._endpoints.items():
            if name == 'METHODS':
                # Métodos HTTP de este endpoint.
                for api_method, doc in content:
                    name = api_method.lower()
                    obj_method = partial(self._api_call, name)
                    obj_method.__doc__ = self._unpack_doc(doc)
                    setattr(self, name, obj_method)
            elif name.startswith('_') and name.endswith('_'):
                # Argumento de la API
                self._allowed_args.append(name.strip('_'))
            else:
                # Path parcial de la API.
                next_path = TrelloAPI(endpoints=self._endpoints[name],
                                      name=name,
                                      apikey=self._apikey,
                                      parent=self)
                setattr(self, name, next_path)

    @staticmethod
    def _unpack_doc(b64):
        return gzip.decompress(b64decode(b64)).decode('utf-8')

    @property
    def _url(self):
        """
        Resolve the URL to this point.

        >>> trello = TrelloAPIV1('APIKEY')
        >>> trello.batch._url
        '1/batch'
        >>> trello.boards(board_id='BOARD_ID')._url
        '1/boards/BOARD_ID'
        >>> trello.boards(board_id='BOARD_ID')(field='FIELD')._url
        '1/boards/BOARD_ID/FIELD'
        >>> trello.boards(board_id='BOARD_ID').cards(filter='FILTER')._url
        '1/boards/BOARD_ID/cards/FILTER'

        """
        if self._api_arg:
            mypart = str(self._api_arg)
        else:
            mypart = self._name

        if self._parent:
            return '/'.join(filter(None, [self._parent._url, mypart]))
        else:
            return mypart

    def _api_call(self, method_name, *args, **kwargs):
        """
        Makes the HTTP request.

        """
        kwargs.setdefault('params', {}).update({'key': self._apikey})

        http_method = getattr(requests, method_name)
        return http_method(TRELLO_URL + self._url, *args, **kwargs)

    def __call__(self, **kwargs):
        """
        Adds a variable parameter to the API URL.

        """
        if not kwargs:
            raise ValueError("A keyword argument must be provided: {}".format(
                                ', '.join(self._allowed_args)))
        elif len(kwargs) > 1:
            raise ValueError("Too many arguments.")
        elif set(kwargs.keys()) <= set(self._allowed_args):
            _name, _api_arg = list(kwargs.items())[0]
            name = '_' + _name + '_'
            return TrelloAPI(endpoints=self._endpoints[name],
                             name=name,
                             apikey=self._apikey,
                             parent=self,
                             api_arg=_api_arg)
        else:
            raise ValueError("Unknown argument {}".format(kwargs.keys()))

    def __repr__(self):
        return 'TrelloQuery <"{}">'.format(self._url)


def generate_api(version):
    """
    Generates a factory function to instantiate the API with the given
    version.

    """
    def get_partial_api(key):
        return TrelloAPI(ENDPOINTS[version], version, key)

    get_partial_api.__doc__ = \
        """Interfaz REST con Trello. Versión {}""".format(version)

    return get_partial_api

#
# Generate and register a TrelloAPI class for each version.
#
for version in ENDPOINTS.keys():
    api_cls = generate_api(version)
    api_name = 'TrelloAPIV{}'.format(version)

    globals()[api_name] = api_cls

    __all__.append(api_name)
