# -*- coding: utf-8 -*-
import logging

from tater.core import RegexLexer, Rule, bygroups
from tater.tokentype import Token
from tater.common import re_divisions


class Tokenizer(RegexLexer):
    DEBUG = logging.INFO

    r = Rule
    t = Token
    re_skip = '[\s,\xa0]+'
    dont_emit = (t.Junk,)

    tokendefs = {
        'root': [
            r(t.Type, '(?i)An? (BILL|Act)', 'impact'),
            ],

        'impact': [
            r(t.Junk, 'to'),
            r(t.Junk, 'and'),
            r(t.Amend.AndReenact, 'amend and reenact', 'enumeration'),
            r(t.Amend, 'amend', 'enumeration'),
            r(t.Repeal, 'repeal', 'enumeration'),
            r(t.Semicolon, ';'),
            r(t.Source.VACode, 'the Code of Virginia', 'opcodes'),
            ],

        'enumeration': [
            r(t.SecSymbol, r'[\xa7]+'),
            # r(t.Enumeration, r'((?:[\d][\w\.]?)(?:[\-\w\.]+)?)'),
            r(t.Enumeration, r'(?:[\d][\w\.:\-]*)'),
            r(t.And, 'and'),
            r(t.Source.VACode, 'of the Code of Virginia'),
            r(bygroups(t.SessionLaws.Name, t.SessionLaws.Year),
              'the (Acts of Assembly) of (\d{4})'),
            r(t.Numbered, 'numbered'),
            r(t.Of, 'of'),
            r(t.Division, re_divisions),
            r(t.Qualification.Conditional, 'as it may become effective'),
            r(t.Qualification.Current, 'as it is currently effective'),
            # r(t.RelatingTo, 'relating to .+'),
            # r(t.WhichProvided, 'which provided .+')
            ],

        'opcodes': [
            r(t.ByAdding, 'by adding'),
            r(t.Division, re_divisions, 'enumeration'),
            r(t.In, 'in'),
            r(t.A, 'a'),
            ]
        }
