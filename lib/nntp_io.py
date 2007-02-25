# -*- coding: utf-8 -*-

# Flrn-gtk: interface avec le serveur de news et formatage des articles
# Rémy Oudompheng, Noël 2005

import nntplib
import sys, time
import re
find_encoding_regexp = re.compile("charset=(\"[^\"]*\"|[^ ]*)")
rfc2047_regexp = re.compile("(=\?[^?]*\?[bqBQ]\?[^ ?]*\?=)")
header_regexp = re.compile("([^ :]*): (.*)")

import email.Header
import email.Utils
import flrn_config
from data_types import *

# Codes valides :
# 211 GROUP
# 215 LIST
# 220 ARTICLE
# 221 HEAD
# 222 BODY
# 223 STAT
# 224 XOVER

def fill_tree(data, notree=False):
    """Vérifié à minuit le 21 décembre.
    data = [ [groupe, données] ... ]
    result = [ ["label1", [branche1 = [label, [subbranch1, ...]], ...]
               ["label2", [branche1, ...]]"""
    if notree:
        return [["", dat[1], True] for dat in data]
    if len(data) == 0:
        return []
    elif (len(data) == 1) and (data[0][0] == ''):
        # Une feuille (3 éléments)
        return [['', data[0][1], True]]
    else:
        result = []
        while len(data) > 0:
            # Première branche
            ref = data[0][0]
            branch = ref.split(".")[0]
            interesting = []
        
            # On récupère les descendants de la branche
            i = 0
            while i < len(data):
                if data[i][0].split(".")[0] == branch:
                    node, metadata = data.pop(i)
                    node = node.split(".", 1)
                    if len(node) == 1:
                        interesting.append(["", metadata])
                    else:
                        interesting.append([node[1], metadata])
                else:
                    i += 1
            # On crée un arbre à partir de la branche
            if branch == "":
                result.append(fill_tree(interesting)[0])
                # C'est une feuille à 3 éléments
            else:
                result.append([branch, fill_tree(interesting)])
                # C'est un noeud à deux éléments
        return result;

class NewsServer:
    "Serveur de News"
    def __init__(self, address = "clipper.ens.fr", port = 2019):
        self.address = address
        self.port = port
        self.cache = {}
        self.socket = nntplib.NNTP(self.address, self.port)

        self.needs_auth = False
        self.username = ""
        self.password = ""
        # On vérifie s'il faut une authentification.
        try:
            self.socket.last()
        except nntplib.NNTPTemporaryError, item:
            if item.args[0].startswith("480"):
                self.needs_auth = True

    def authenticate(self, user, passwd):
        try:
            self.socket.quit()
        except:
            pass
        self.username = user
        self.password = passwd
        self.socket = nntplib.NNTP(self.address, self.port,
                                   user, passwd)

    def retry_connect(self):
        if self.needs_auth:
            self.socket = nntplib.NNTP(self.address, self.port,
                                       self.username, self.password)
        else:
            self.socket = nntplib.NNTP(self.address, self.port)
    
    def overview(self, group, start, end):
        """Renvoie l'overview de /group/ entre /start/ et /end/
        result = [ [num, subj, from, date, msgid, refs, size, lines]* ],
        ainsi que la liste des messages inexistants"""
        if end < start:
            return ([], [])
        try:
            resp, count, first, last, name = self.socket.group(group)
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                resp, count, first, last, name = self.socket.group(group)
        start = max(start, int(first))
        end = min(end, int(last))
        resp, result = self.socket.xover(str(start), str(end))

        if resp.startswith("224"):
            return result, [start, end]
        else:
            return None

    def group_stats(self, group):
        """Renvoie le numéro du premier et du dernier article"""
        try:
            resp, count, first, last, name = self.socket.group(group)
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                resp, count, first, last, name = self.socket.group(group)
        if resp.startswith("211"):
            return [int(first), int(last)]
        else:
            return None

    def get_article_by_msgid(self, msgid):
        if msgid in self.cache:
            return self.cache[msgid]
        else:
            raw = self.get_by_msgid(msgid)
            if raw:
                art = Article()
                art.from_nntplib(raw)
                self.cache[msgid] = art
                return art
            else:
                return None

    def get_by_msgid(self, msgid):
        """Renvoie les en-têtes et le corps du message /msgid/"""
        try:
            resp, respcode, id, headers = self.socket.head(msgid)
            resp, respcode, id, body = self.socket.body(msgid)
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                resp, respcode, id, headers = self.socket.head(msgid)
                resp, respcode, id, body = self.socket.body(msgid)
        except nntplib.NNTPTemporaryError:
            #if resp.startswith("430"):
            return None
        if resp.startswith("222"):
            return [headers, body]
        else:
            return None

    def get_by_artno(self, group, artno):
        """Renvoie le msgid de /group:artno/"""
        try:
            self.socket.group(group)
            resp, num, msgid = self.socket.stat(str(artno))
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                self.socket.group(group)
                resp, num, msgid = self.socket.stat(str(artno))
        except nntplib.NNTPTemporaryError:
            #if resp.startswith("430"):
            return None
        if resp.startswith("223"):
            return msgid
        else:
            return None

    def post_article(self, file):
        """Poste un article et renvoie le message d'erreur"""
        try:
            resp = self.socket.post(file)
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                self.socket.group(group)
                resp = self.socket.post(file)
        except nntplib.TemporaryError, handler:
            return u"Erreur. Réponse du serveur " + handler.args[0]
        if resp.startswith("240"):
            return None
        else:
            return u"Erreur. Réponse du serveur " + resp
        return None

    def groups_list(self):
        try:
            code, group_list = self.socket.list()
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timeout'):
                # On relance la connexion
                self.retry_connect()
                code, group_list = self.socket.list()
        if not(code.startswith("215")):
            return []
        else:
            return dict([(name, [int(n1), int(n2)])
                         for name, n2, n1, postable in group_list])
