# -*- coding: utf-8 -*-

# Flrn-gtk: Traitement du killfile
# Rémy Oudompheng, Mai 2006

import sys
import re
import flrn_config
from data_types import *
match_regexp = re.compile('^:(.*):([^:]*)')
rule_regexp = re.compile("^\*(\^?)('?)([^:]*):(.*)")
RULE_REGEXP = 0
RULE_LIST = 1
RULE_FILE = 2

OVERVIEW_CONTENTS = [
    'Subject',
    'From',
    'Date',
    'Message-ID',
    'References' ]

class KillRuleCondition:
    def match_re(self, string):
        """Match sur regexp"""
        m = self.rule.match(string)
        if m and (m.start() == 0) and (m.end() == len(string)):
            debug_output('[Killfile] Match ' + string
                         + ' on ' +  self.header + " : "
                         + self.rule.pattern)
            return not self.negate
        return self.negate
    
    def match_sub(self, string):
        """Match sur sous-chaîne"""
        return (self.negate != (self.rule in string))
    
    def __init__(self, line):
        data = rule_regexp.match(line)
        if not(data):
            self.killme = True
        else:
            self.killme = False
            self.negate = data.group(1) == '^'
            self.header = data.group(3).strip()
            if data.group(2) == "'":
                self.rule = data.group(4).strip()
                self.match = self.match_sub
            else:
                self.rule = re.compile(data.group(4).strip())
                self.match = self.match_re

class KillRule:
    # group_rule: règle de choix du groupe
    # art_rules: règles de choix de l'article
    def group_re_match(self, string):
        """Matche un groupe selon (re)self.group_rule"""
        m = self.group_rule.match(string)
        if m and (m.start() == 0) and (m.end() == len(string)):
            debug_output('[Killfile] Match ' +  string 
                                     + ' on ' + self.group_rule.pattern)
            return True
        return False

    def group_list_match(self, string):
        """Matche un groupe selon (string*)self.group_rule"""
        if string in self.group_rule:
            debug_output('[Killfile] Match ' +  string 
                                     + ' in list ' + repr(self.group_rule))
            return True
        return False

    def article_match(self, headers):
        """Vérifie les règles dans le dictionnaire headers"""
        for c in self.conditions:
            if not((c.header in headers) and (c.match(headers[c.header]))):
                return False
        return True

    def __init__(self, lines, config_dir):
        # Membres
        self.group_rule = []
        self.group_match = self.group_list_match
        self.conditions = []
        # Changements apportés pur la règle
        self.read_before = False
        self.read_after = True
        # Suicide
        self.killme = False
        # Initialise une règle à partir d'une entrée du kill-file
        # lines est une liste de lignes sans \n
        lines = [i.strip() for i in lines if not i.startswith('#')]
        if len(lines) == 0:
            self.killme = True
            return
        # La première ligne 
        matching = match_regexp.match(lines[0].strip())
        if matching:
            data = matching.group(1)
            flags = matching.group(2)
            if flags == '':
                # Cas des regexps
                self.group_rule = re.compile(data)
                self.match_rule = RULE_REGEXP
                self.group_match = self.group_re_match
            elif flags == 'l':
                # Cas des listes
                self.group_rule = [data]
                self.match_rule = RULE_LIST
                self.group_match = self.group_list_match
            elif 'f' in flags:
                # Cas des fichiers listes
                f = open(config_dir.rstrip("/") + '/' + data)
                if f:
                    self.group_rule = [l.strip() for l in f.readlines()]
                    f.close()
                self.match_rule = RULE_FILE
                self.group_match = self.group_list_match
        else:
            self.killme = True
            return None
        # Lecture des autres lignes
        for l in lines[1:]:
            # Ligne de liste
            if (l[0] == ':') and (match_rule == RULE_LIST):
                self.group_rule.append(l)
            # Ligne de règle
            if l[0] == '*':
                c = KillRuleCondition(l)
                if c.killme:
                    del c 
                else:
                    self.conditions.append(c)
            # Ligne d'action
            if l[0] == 'T':
                self.read_after = ((l in ['Tread', 'Tkilled'])
                                   and (l not in ['Tunread', 'Tunkilled']))
            # Ligne de flag
            if l[0] == 'F':
                self.read_before = ((l in ['Fread', 'Fkilled'])
                                   and (l not in ['Funread', 'Funkilled']))

        # A-t-on besoin de l'article entier ?
        for i in self.conditions:
            if i.header not in OVERVIEW_CONTENTS:
                self.needs_overview = True
            else:
                self.needs_overview = False
        if len(self.conditions) == 0:
            # Provisoirement
            self.killme = True
                
            
        
        
