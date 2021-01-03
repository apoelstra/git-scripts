#!/bin/python

from concurrent import futures
from typing import List

def json_object_hook(dct):
    if 'type' not in dct:
        raise KeyError('test commands must have the "type" field')

    for cls in Check.__subclasses__():
        if dct['type'] == cls.TYPE:
            return cls(dct)

    raise KeyError(f"test type {dct['type']} did not match any known types")

class Check:
    def __init__(self, json):
        self.only_tip = json.get('only-tip', False)

    def run(self, executor: futures.ThreadPoolExecutor, commit: str, notes: List[str]):
        raise NotImplementedError()

from checks import autotools,rust,wasm_pack

