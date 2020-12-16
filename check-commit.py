#!/bin/python

from util.git import TemporaryWorkdir
from util.cargo import Cargo
from util.notes import attach_note

MSRV = 1.29

notes = []

stable = Cargo()
version = stable.version_str()
print ("Version ", version)

with TemporaryWorkdir() as workdir:
    print ("Git: ", workdir)


