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
            if handler.args[0].startswith('503 Timoeout'):
                # On relance la connexion
                self.retry_connect()
                resp, count, first, last, name = self.socket.group(group)
        start = max(start, int(first))
        end = min(end, int(last))
        resp, result = self.socket.xover(str(start), str(end))

        if resp.startswith("224"):
            vanished = []
            articles = [int(a[0]) for a in result]
            articles.append(end + 1)
            articles.insert(0, start - 1)
            for i in xrange(1, len(articles)):
                if (articles[i] - articles[i - 1]) > 1:
                    vanished.extend(range(
                        articles[i - 1] + 1, articles[i]))
            return (result, vanished)
        else:
            return None

    def group_stats(self, group):
        """Renvoie le numéro du premier et du dernier article"""
        try:
            resp, count, first, last, name = self.socket.group(group)
        except nntplib.NNTPPermanentError, handler:
            if handler.args[0].startswith('503 Timoeout'):
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
            if handler.args[0].startswith('503 Timoeout'):
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
            if handler.args[0].startswith('503 Timoeout'):
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
            if handler.args[0].startswith('503 Timoeout'):
                # On relance la connexion
                self.retry_connect()
                code, group_list = self.socket.list()
        if not(code.startswith("215")):
            return []
        else:
            return dict([(name, [int(n1), int(n2)])
                         for name, n2, n1, postable in group_list])

# Traitement des en-têtes
def translate_header(header):
    """Décode un entête "selon" la RFC2047"""
    s = header.decode("latin-1")
    todo = True
    while todo:
        todo = rfc2047_regexp.search(s)
        if todo:
            encoded = todo.group(1).replace(' ', '')
            try:
                decoded = email.Header.decode_header(encoded)
            except UnicodeDecodeError:
                break
            try:
                decoded = decoded[0][0].decode(decoded[0][1])
            except (LookupError, UnicodeDecodeError):
                sys.stderr.write("[Encodage foireux] " + repr(header) + '\n')
                decoded = decoded[0][0].decode('latin-1')
            s = s.replace(encoded, decoded)
    return s
    
def untranslate_header(header, encoding):
    """Encode un en-tête"""
    words = header.split(" ")
    s = ""
    for w in words:
        try:
            s += w.encode('us-ascii') + " "
        except:
            s += email.Header.Header(w, encoding).encode() + " "
    return s[:-1]

# Conversions sur les articles
class Article:
    def from_nntplib(self, nntplib_list):
        """Lit un article au format [ [header1, header2...],
                                      [ligne1, ligne2,...] ]"""
        if not(nntplib_list):
            return False
        # En-têtes
        del self.headers
        headers_tmp = []
        for h in nntplib_list[0]:
            test = header_regexp.match(h)
            if test:
                headers_tmp.append([test.group(1), test.group(2)])
            else:
                if len(headers_tmp) > 0:
                    headers_tmp[-1][1] += h.strip()
        # Encodage
        charset = "latin-1"

        self.headers = dict(
            [(h[0], translate_header(h[1])) for h in headers_tmp])
        try:
            if (self.headers["Content-Transfer-Encoding"].lower().strip()
                == "quoted-printable"):
                nntplib_list[1] = '\n'.join(
                    nntplib_list[1]).decode('quopri_codec').split('\n')
            if (self.headers["Content-Transfer-Encoding"].lower().strip()
                == 'base64'):
                nntplib_list[1] = '\n'.join(
                    nntplib_list[1]).decode('base64_codec').split('\n')
        except KeyError: pass
        try:
            found = find_encoding_regexp.search(self.headers['Content-Type'])
            if found:
                charset = found.group(1).strip('"')
        except KeyError: pass

        # Corps
        self.body = ''
        for l in nntplib_list[1]:
            try:
                self.body += l.decode(charset) + '\n'
            except (LookupError, UnicodeDecodeError):
                print >> sys.stderr, \
                    '[Encodage foireux] Soi-disant', charset
                print >> sys.stderr, '    ' + repr(l)
                self.body += l.decode('latin-1') + '\n'
        return True

    def from_utf8_text(self, text, config):
        """Prépare un article pour l'envoi"""
        parts = text.split('\n\n', 1)
        header_part = parts[0].split('\n')
        output = ''

        # Lecture des en-têtes
        del self.headers
        self.headers = {}
        for l in header_part:
            t = header_regexp.match(l)
            if t:
                self.headers[t.group(1)] = t.group(2)
        for myhdr, t in config.my_hdrs.iteritems():
            if not(self.headers.has_key(myhdr)):
                self.headers[myhdr] = t
                
        self.body = parts[1]

    def to_raw_format(self, config):
        for h in self.headers:
            if h == 'From':
                # Python encode n'importe comment
                name, addr = email.Utils.parseaddr(self.headers[h])
                name = untranslate_header(name, self.encoding)
                addr = untranslate_header(addr, self.encoding)
                self.headers[h] = addr + ' (' + name + ')'
            else:
                self.headers[h] = untranslate_header(
                    self.headers[h], self.encoding)

        # Choix d'un encodage
        encodings = [a.strip('\'"') for a in 
                     config.params['post_charsets'].split()]
        encodings[0:0] = ['us-ascii']
        encodings[0:0] = ['us-ascii']
        encodings.append('utf-8')

        try:
            # Recherche d'un encodage défini par l'utilisateur
            found = find_encoding_regexp.search(self.headers['Content-Type'])
            if found:
                encodings[0:0] = [found.group(1).strip('"')]
        except KeyError:
            pass
        
        encoding = None
        for enc in encodings:
            try:
                body_encoded = self.body.encode(enc)
                encoding = enc
                break
            except UnicodeError:
                continue
        if encoding == None: return None

        self.headers['Content-Type'] = 'text/plain;charset=' + encoding

        try:
            if (self.headers['Content-Transfer-Encoding']
                in ['base64', 'quoted-printable']):
                body_encoded = body_encoded.encode(
                    self.headers['Content-Transfer-Encoding'])
        except KeyError:
            self.headers['Content-Transfer-Encoding'] = '8bit'

        output = '\n'.join([h + ': ' + self.headers[h]
                            for h in self.headers]).encode('us-ascii')
        output += '\n\n'
        output += body_encoded
        return output

    def __init__(self, encoding = "iso-8859-1"):
        self.headers = {}
        self.body = ""
        self.encoding = encoding
