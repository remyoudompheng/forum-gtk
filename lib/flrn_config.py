# -*- coding: utf-8 -*-

# Flrn-gtk: Interface avec les fichiers de configuration de flrn
# Rémy Oudompheng, Noël 2005

import os
import socket
from pwd import getpwuid
import re,time
import string, locale
import email.Utils
import nntp_io
import sys

from article_killer import *

# Constantes
PROGRAM_VERSION = "0.7"
debug_fd = sys.stderr

def debug_output(string):
    print >> debug_fd, string.encode(locale.getpreferredencoding())

# Expressions régulières du flrnrc
encoding_regexp = re.compile(
    "set +files_charset(?:=| +)(.*[^ ]).*\n")
namedoption_regexp = re.compile("name +([^ ]*) +(.*\n)")
setfalse_regexp = re.compile(
    "set +no([^ =]*) *\n")
settrue_regexp = re.compile(
    "set +([^ =]*) *\n")
setvalue_regexp = re.compile(
    "set +([^ =]*)(?:=| +)(.*[^ ]) *\n")
myheader_regexp = re.compile(
    "my_hdr +([^ ]*): +(.*[^ ]) *\n")
showheader_regexp = re.compile(
    "header +([^ ]*) +(.*) *\n")

# Expressions régulières du newsrc
newsrc_regexp = re.compile("([^ !:]*)(:|!) +(.*) *\n")

reply_regexp = re.compile("^[Rr][Ee] *:")

headers_nb = [
    'From', u'Réponse à', 'Subject', 'Date',
    'Newsgroups', 'Followup-To', 'Organization', 'Lines',
    'Sender', 'Reply-To', 'Expires', 'X-Newsreader']

def is_geek_time(start, end):
    """Est-ce vraiment le moment de lire forum ?"""
    if not(re.match("[0-2][0-9]:[0-5][0-9]", start)):
        print start, ": mauvais format d'heure"
        return True
    if not(re.match("[0-2][0-9]:[0-5][0-9]", end)):
        print end, ": mauvais format d'heure"
        return True
    start = start.split(":")
    end = end.split(":")
    s = int(start[0]) * 60 + int(start[1])
    t = time.localtime().tm_hour * 60 + time.localtime().tm_min
    u = int(end[0]) * 60 + int(end[1])
    if s <= u:
        return (s <= t <= u)
    else:
        return not(u <= t <= s)

class PercentTemplate(string.Template):
    delimiter='%'

class FlrnConfig:
    def make_reply(self, original):
        # En-têtes de la réponse
        reply = nntp_io.Article()
        if 'Followup-To' in original.headers:
            reply.headers["Newsgroups"] = original.headers['Followup-To']
        else:
            reply.headers["Newsgroups"] = original.headers['Newsgroups']
        if 'References' in original.headers:
            reply.headers["References"] = original.headers['References'] + ' ' + original.headers['Message-ID']
        else:
            reply.headers['References'] = original.headers['Message-ID']
        if reply_regexp.match(original.headers['Subject']):
            reply.headers['Subject'] = original.headers['Subject']
        else:
            reply.headers["Subject"] = u'Re: ' + original.headers["Subject"]
        reply.headers['From'] = self.from_header

        # Ligne d'attribution
        author = email.Utils.parseaddr(original.headers['From'])
        xref = original.headers['Xref'].split()[1].split(':')
        group_parts = xref[0].split('.')
        group_abbr = u""
        for a in group_parts[:-1]: group_abbr += a[0] + "."
        group_abbr += group_parts[-1]

        if author[0]:
            author = author[0]
        else:
            author = author[1]

        if not(self.params['include_in_edit']):
            reply.body = ""
            return reply
        
        body = PercentTemplate(self.params['attribution']).safe_substitute(
            n=author,
            i=original.headers['Message-ID'],
            G=xref[0],C=xref[1],
            g=group_abbr) + '\n'

        # Citation
        prefix = self.params['index_string']
        if self.params['smart_quote'] and self.params['index_string'].endswith(' '):
            lines = original.body.split('\n')
            short_prefix = prefix.rstrip()
            for i in range(len(lines)):
                if lines[i].startswith('>'):
                    body = body + short_prefix + lines[i] + '\n'
                else:
                    body = body + prefix + lines[i] + '\n'
        else:
            body = body + prefix + original.body.replace('\n', '\n' + prefix)

        reply.body = body
        return reply

    def load_newsrc(self):
        """Renvoie un dictionnaire {groupe -> [liste des lus]}
        et deux ensembles de groupes abonnés et non-abonnés"""
        # Lecture du newsrc
        newsrc_path = self.config_dir + "/.flnewsrc" + self.params['flnews_ext']
        try:
            source = open(newsrc_path, 'r')
        except IOError:
            try:
                source = open(newsrc_path, 'w')
                source.close()
                self.subscribed = set([])
                self.unsubscribed = set([])
                self.groups = {}
                self.refresh_groups()
                return None
            except IOError:
                return None
        newsrc = source.readlines()
        source.close()
        
        # Lecture des données
        self.subscribed = set([])
        self.unsubscribed = set([])
        self.groups = {}
        for l in newsrc:
            t = newsrc_regexp.match(l)
            if t:
                if t.group(2) == ":":
                    self.subscribed.add(t.group(1))
                elif t.group(2) == "!":
                    self.unsubscribed.add(t.group(1))
                try:
                    self.groups[t.group(1)] = [
                        [int(n) for n in k] 
                        for k in [rng.split('-') 
                                  for rng in t.group(3).split(',')]]
                except ValueError:
                    self.groups[t.group(1)] = []

        # On évite les grotesquitudes
        self.unsubscribed -= self.subscribed
                
    def register_read(self, group, number):
        """Marque comme lu"""
        nos = self.groups[group]
        # On vérifie s'il est déjà lu.
        read = False
        for rng in nos:
            if rng[0] <= number <= rng[-1]:
                read = True
        if read:
            return
        else:
            self.unreads[group] -= 1

        if len(nos) == 0:
            nos.append([number])
            return
        
        if number < nos[0][0]:
            nos.insert(0, [number])
        elif number > nos[-1][-1]:
            nos.append([number])
        else:
            for i in xrange(len(nos)):
                if number == (nos[i][0] - 1):
                    nos[i] = [nos[i][0] - 1, nos[i][-1]]
                    break
                elif number == (nos[i][-1] + 1):
                    nos[i] = [nos[i][0], nos[i][-1] + 1]
                    break
                if (i > 0) and (nos[i - 1][-1] < number < nos[i][0]):
                    nos.insert(i, [number])
                    break

        # Fusion
        for i in xrange(1, len(nos)):
            if (nos[i][0] - nos[i - 1][-1]) <= 1:
                nos[i-1:i+1] = [[nos[i - 1][0], nos[i][-1]]]
                break
        
    def register_unread(self, group, number):
        """Marque comme non-lu"""
        nos = self.groups[group]
        # On vérifie s'il est déjà lu.
        read = False
        for rng in nos:
            if rng[0] <= number <= rng[-1]:
                read = True
        if not read:
            return
        else:
            self.unreads[group] -= 1

        for i in xrange(len(nos)):
            if number == nos[i][0]:
                if len(nos[i]) == 1:
                    del nos[i]
                else:
                    nos[i] = [nos[i][0] + 1, nos[i][-1]]
                    if nos[i][0] == nos[i][1]:
                        del nos[i][1]
                break
            elif number == nos[i][-1]:
                if len(nos[i]) == 1:
                    del nos[i]
                else:
                    nos[i] = [nos[i][0], nos[i][-1] - 1]
                    if nos[i][0] == nos[i][1]:
                        del nos[i][1]
                break
            elif (nos[i][0] < number < nos[i][-1]):
                nos[i:i+1] = [[nos[i][0], number - 1],
                                    [number + 1, nos[i][-1]]]
                if nos[i][0] == nos[i][1]:
                    del nos[i][1]
                if nos[i+1][0] == nos[i+1][1]:
                    del nos[i+1][1]
                break
        # Fusion
        for i in xrange(1, len(nos)):
            if (nos[i][0] - nos[i - 1][-1]) <= 1:
                nos[i-1:i+1] = [[nos[i - 1][0], nos[i][-1]]]
                break
    
    def save_newsrc(self):
        """Enregistre le newsrc"""
        newsrc_path = (self.config_dir + "/.flnewsrc"
                       + self.params['flnews_ext'])
        # Lecture de l'ordre
        try:
            source = open(newsrc_path, 'r')
            order = [l.split(':')[0].split('!')[0] for l in source.readlines()]
            source.close()
        except:
            order = []
            pass
        new_subs = []
        new_unsubs = []

        if os.access(newsrc_path, os.W_OK):
            os.rename(newsrc_path, newsrc_path + '~')
        f = open(newsrc_path, 'w')

        # Un peu de nettoyage
        for g in self.groups:
            # Fusion  
            for i in xrange(1, len(self.groups[g])):
                if (self.groups[g][i][0] - self.groups[g][i - 1][-1]) <= 1:
                    self.groups[g][i-1:i+1] = [[self.groups[g][i - 1][0], 
                                                self.groups[g][i][-1]]]
                    break
        
        # Groupes pas nouveaux
        for g in order:
            # Groupes abonnés
            if g in self.subscribed:
                if len(self.groups[g]) == 0:
                    f.write(g + ': \n')
                    continue
                read_list = ','.join(['-'.join([str(n) for n in rng])
                                      for rng in self.groups[g]])
                f.write(g + ': ' + read_list + '\n')
            # Groupes pas abonnés
            if g in self.unsubscribed:
                if len(self.groups[g]) == 0:
                    f.write(g + '! \n')
                    continue
                read_list = ','.join(['-'.join([str(n) for n in rng])
                                      for rng in self.groups[g]])
                f.write(g + '! ' + read_list + '\n')

        # Groupes abonnés
        for g in self.subscribed:
            if g not in order:
                if len(self.groups[g]) == 0:
                    f.write(g + ': \n')
                    continue
                read_list = ','.join(['-'.join([str(n) for n in rng])
                                      for rng in self.groups[g]])
                f.write(g + ': ' + read_list + '\n')
        # Groupes pas abonnés
        for g in self.unsubscribed:
            if g not in order:
                if len(self.groups[g]) == 0:
                    f.write(g + '! \n')
                    continue
                read_list = ','.join(['-'.join([str(n) for n in rng])
                                      for rng in self.groups[g]])
                f.write(g + '! ' + read_list + '\n')
        f.close()
        
    def refresh_groups(self):
        for i in self.server.groups_list():
            if i not in self.groups:
                # Marquer les vieux messages comme lus
                self.groups[i] = []
                if self.params['default_subscribe']:
                    self.subscribed.add(i)
                else:
                    self.unsubscribed.add(i)

    def update_unreads(self):
        """Renvoie le nombre de messages non lus pour les groupes
        abonnés (il faudrait pas non plus complètement bourriner
        les serveurs de News)"""
        del self.unreads
        self.unreads = {}
        for g in self.subscribed:
            ends = self.server.group_stats(g)
            read = self.groups[g]
            # On épure si nécessaire
            while (len(read) > 0) and (read[0][0] < ends[0]):
                if read[0][-1] < ends[0]:
                    del read[0]
                    continue
                if read[0][-1] == ends[0]:
                    read[0] = [read[0][-1]]
                    continue
                if read[0][-1] > ends[0]:
                    read[0] = [ends[0], read[0][-1]]
                    continue
            # On épure de l'autre côté (inutile normalement)
            while (len(read) > 0) and (read[-1][-1] > ends[1]):
                if read[-1][0] > ends[1]:
                    del read[-1]
                    continue
                if read[-1][0] == ends[1]:
                    read[-1] = [read[-1][0]]
                    continue
                if read[-1][0] < ends[1]:
                    read[-1] = [read[-1][0], ends[1]]
                    continue
            # On compte le total moins les articles lus
            num = ends[1] - ends[0] + 1
            for val in read:
                num += val[0] - val[-1] - 1
            self.unreads[g] = num

    def eval_string(self, s):
        if s.startswith("'") and s.startswith("'"):
            # Important d'avoir un eval pour les \n
            return eval(s, {}, {}).decode('utf-8')
        if s.startswith('"') and s.startswith('"'):
            return eval(s, {}, {}).decode('utf-8')
        return s.strip("'\"")
    
    def __init__(self, config_dir, mode):
        # Chargement du flrnrc
        if not(config_dir):
            config_dir = "~/.flrn"
        if not(mode):
            mode = 'forum'

        self.config_dir = os.path.expanduser(config_dir)
        self.config_name = mode
        source = open(self.config_dir.rstrip('/') + "/.flrnrc", 'r')
        rc_file = source.readlines()
        source.close()
        encoding='iso-8859-1'

        self.params = {}
        self.my_hdrs = {}
        self.unreads = {}
        # Trucs utiles
        self.wwwbrowser = "dillo"
        # Paramètres par défaut
        self.params['mail_addr'] = (getpwuid(os.getuid())[0] + '@' + 
                                    socket.getfqdn()).decode(encoding)
        self.params['post_name'] = getpwuid(os.getuid())[4].decode(encoding)
        self.params['server'] = "clipper.ens.fr"
        self.params['port'] = "2019"
        self.params['post_charsets'] = "iso-8859-1"
        self.params['attribution'] = "%n wrote in message %i:"
        self.params['index_string'] = "> "; self.params['smart_quote'] = True
        self.params['flnews_ext'] = ''
        self.params['include_in_edit'] = True
        self.params['prefixe_groupe'] = ''
        self.params['abbr_group_names'] = False
        self.params['max_backtrack'] = 500
        self.params['max_foretrack'] = 500

        self.params['small_tree'] = True
        self.params['with_cousins'] = False
        # Corps des messages de cancel
        self.params['cancel_message'] = 'This message is canceled by Forum-GTK ' + PROGRAM_VERSION
        # Horaires de lecture de forum
        self.params['geek_start_time'] = "00:00"
        self.params['geek_end_time'] = "24:00"
        # Affichage des en-têtes
        self.headers_list = ['Newsgroups', 'Followup-To',
                             'From', 'Subject', 'Date']
        self.headers_hide = []
        self.headers_weak = []
        # À épurer quand on supersede
        self.supersede_remove_headers = frozenset([
            'Path', 'Date', 'Sender', 'Message-ID', 'NNTP-Posting-Host',
            'Mime-Version', 'Content-Type', 'Content-Transfer-Encoding',
            'X-Trace', 'X-Complaints-To', 'NNTP-Posting-Date', 'Xref',
            'User-Agent', 'X-Newsreader', 'Lines'])

        if mode == "forum":
            self.my_hdrs['Organization'] = "Le Forum de l'ENS"
        self.my_hdrs['User-Agent'] = "Forum-GTK " + PROGRAM_VERSION
        
        for i in range(min(3, len(rc_file))):
            grep = encoding_regexp.match(rc_file[i])
            if grep:
                encoding = grep.group(1).strip('"')
                break
        self.encoding = encoding

        # Lecture du flrnrc
        for i in rc_file:
            try:
                line = i.decode(encoding)
            except:
                line = i.decode('latin-1')
            # Option liée à un nom
            t = namedoption_regexp.match(line)
            if t:
                if t.group(1) == mode:
                    line = t.group(2)
            # 1er cas: set no<foobar>
            t = setfalse_regexp.match(line)
            if t:
                self.params[t.group(1)] = False
                debug_output("[FlrnConfig] " + t.group(1) + " set to False")
                continue
            # 2e cas: set <foobar>
            t = settrue_regexp.match(line)
            if t:
                self.params[t.group(1)] = True
                debug_output("[FlrnConfig] " + t.group(1) + " set to True")
                continue
            # 3e cas: set <foobar>=<value>
            t = setvalue_regexp.match(line)
            if t:
                value = t.group(2)
                if (value == "0") or (value == "no"):
                    self.params[t.group(1)] = False
                    debug_output("[FlrnConfig] " + t.group(1) + " set to False")
                elif (value == "1") or (value == "yes"):
                    self.params[t.group(1)] = True
                    debug_output("[FlrnConfig] " + t.group(1) + " set to True")
                else:
                    self.params[t.group(1)] = self.eval_string(value)
                    debug_output("[FlrnConfig] " + t.group(1)
                                 + " set to " + repr(self.params[t.group(1)]))
                continue
            # 4e cas: my_hdr Foobar: Value
            t = myheader_regexp.match(line)
            if t:
                self.my_hdrs[t.group(1)] = self.eval_string(t.group(2))
                debug_output("[FlrnConfig] Header %s set to %s" %
                             (t.group(1), repr(self.my_hdrs[t.group(1)])))
                continue
            # 5e cas: header (list|hide)
            t = showheader_regexp.match(line)
            if t:
                if t.group(1) == "list":
                    self.headers_list = t.group(2).split()
                elif t.group(1) == "hide":
                    self.headers_hide = t.group(2).split()
                elif t.group(1) == 'weak':
                    self.headers_weak = t.group(2).split()
        # Fin de la lecture du flrnrc
        
        # Conversion des numéros des en-têtes
        for i in range(len(self.headers_list)):
            try:
                self.headers_list[i] = headers_nb[int(self.headers_list[i]) - 1]
            except (ValueError, IndexError):
                pass
        for i in range(len(self.headers_hide)):
            try:
                self.headers_hide[i] = headers_nb[int(self.headers_hide[i]) - 1]
            except (ValueError, IndexError):
                pass
        for i in range(len(self.headers_weak)):
            try:
                self.headers_weak[i] = headers_nb[int(self.headers_weak[i]) - 1]
            except (ValueError, IndexError):
                pass

        # Préparation du serveur.
        self.from_header = self.params['mail_addr'] + ' (' + self.params['post_name'] + ')'

        self.server = nntp_io.NewsServer(
            self.params['server'], int(self.params['port']))
        
        # Lecture du newsrc
        self.load_newsrc()

        # Lecture du killfile
        self.killrules = []
        if 'kill_file_name' in self.params:
            debug_output("[FlrnConfig] Ouverture de %s" % 
                         self.params['kill_file_name'])
            try:
                f = open(self.config_dir.rstrip('/')
                         + '/' + self.params['kill_file_name'], 'r')
                debug_output("[FlrnConfig] Ouvert "
                             + self.params['kill_file_name'])
                for t in f.read().split("\n\n"):
                    k = KillRule(t.strip("\n").split("\n"), self.config_dir)
                    if not k.killme:
                        self.killrules.append(k)
                f.close()
            except IOError, (errno, truc):
                debug_output("[FlrnConfig] Erreur %s : %s" % (errno, truc))
                pass
        

                
