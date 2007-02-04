# -*- coding: utf-8 -*-

# Flrn-gtk: classes de données
# Rémy Oudompheng, Noël 2005-Printemps 2007

import string, sys, locale

debug_fd = sys.stderr
def debug_output(string):
    print >> debug_fd, string.encode(locale.getpreferredencoding())

class PercentTemplate(string.Template):
    delimiter='%'

class ArticleRange(list):
    """Contient une liste de singletons ou de couples représentant un
    ensemble fini d'entiers"""
    def __init__(self, numbers):
        if not(numbers): return
        if (isinstance(numbers, list)
            and isinstance(numbers[0], int)
            and isinstance(numbers[-1], int)):
            self[:] = [[numbers[0], numbers[-1]]]
            return
        if numbers.strip():
            self[:] = [[int(n) for n in k] for k in
                       [rng.split('-') for rng in numbers.split(',')]]

    def cleanup(self):
        """Nettoyage"""
        i = 1
        while i < len(self):
            if ((self[i][0] - self[i - 1][-1]) <= 1) and (self[i][-1] >= self[i - 1][0]):
                self[i-1:i+1] = [[self[i - 1][0],
                                  max(self[i - 1][-1], self[i][-1])]]
                continue
            i += 1

    def trim(self, ends):
        """On épure si nécessaire"""
        while (len(self) > 0) and (self[0][0] < ends[0]):
            if self[0][-1] < ends[0]:
                del self[0]
                continue
            if self[0][-1] == ends[0]:
                self[0] = [self[0][-1]]
                continue
            if self[0][-1] > ends[0]:
                self[0] = [ends[0], self[0][-1]]
                continue
        # On épure de l'autre côté (inutile normalement)
        while (len(self) > 0) and (self[-1][-1] > ends[1]):
            if self[-1][0] > ends[1]:
                del self[-1]
                continue
            if self[-1][0] == ends[1]:
                self[-1] = [self[-1][0]]
                continue
            if self[-1][0] < ends[1]:
                self[-1] = [self[-1][0], ends[1]]
                continue

    def to_string(self):
        return (
            ','.join(
                ['-'.join([str(n) for n in rng])
                 for rng in self]
            )
        ) if len(self) > 0 else ''

    def how_many(self):
        return sum([r[-1] - r[0] for r in self]) + len(self)

    def owns(self, number):
        for i in self:
            if i[0] <= number <= i[-1]:
                return True
        return False
    
    def add_item(self, number):
        """Marque comme lu"""
        if self.owns(number): return False
        if len(self) == 0:
            self.append([number])
            return        
        if number < self[0][0]:
            self.insert(0, [number])
        elif number > self[-1][-1]:
            self.append([number])
        else:
            for i in xrange(len(self)):
                if number == (self[i][0] - 1):
                    self[i] = [self[i][0] - 1, self[i][-1]]
                    break
                elif number == (self[i][-1] + 1):
                    self[i] = [self[i][0], self[i][-1] + 1]
                    break
                if (i > 0) and (self[i - 1][-1] < number < self[i][0]):
                    self.insert(i, [number])
                    break
        self.cleanup()
        return True

    def del_item(self, number):
        """Marque comme non lu"""
        if not self.owns(number): return False

        for i in xrange(len(self)):
            if number == self[i][0]:
                if len(self[i]) == 1:
                    del self[i]
                else:
                    self[i] = [self[i][0] + 1, self[i][-1]]
                    if self[i][0] == self[i][1]:
                        del self[i][1]
                break
            elif number == self[i][-1]:
                if len(self[i]) == 1:
                    del self[i]
                else:
                    self[i] = [self[i][0], self[i][-1] - 1]
                    if self[i][0] == self[i][1]:
                        del self[i][1]
                break
            elif (self[i][0] < number < self[i][-1]):
                self[i:i+1] = [[self[i][0], number - 1],
                                    [number + 1, self[i][-1]]]
                if self[i][0] == self[i][1]:
                    del self[i][1]
                if self[i+1][0] == self[i+1][1]:
                    del self[i+1][1]
                break
        self.cleanup()
        return True

    def add_range(self, range):
        """Ajoute un intervalle"""
        if len(self) == 0:
            self.append([range[0], range[1]])
        else:
            # Insertion du bouzin
            for i in xrange(len(self)):
                if (range[0] - 1 <= self[i][-1]):
                    if range[1] < self[i][0] - 1:
                        self[i:i] = [[range[0], range[1]]]
                        break
                    elif self[i][0] - 1 <= range[1] :
                        self[i] = [min(self[i][0], range[0]),
                                  max(self[i][-1], range[1])]
                    break
        self.cleanup()
        return True

    def del_range(self,range):
        """Ajoute un intervalle"""
        i = 0
        while i < len(self):
            if range[0] <= self[i][0]:
                if range[1] >= self[i][-1]:
                    # On enlève tout
                    del self[i]
                    continue
                else:
                    # On enlève par la gauche
                    self[i][0] = range[1] + 1
                    break
            if self[i][0] < range[0]:
                if self[i][-1] > range[1]:
                    # On enlève au milieu
                    self[i:i+1] = [[self[i][0], range[0] - 1],
                                  [range[1] + 1, self[i][-1]]]
                    break
                else:
                    if self[i][-1] >= range[0]:
                        # On enlève à droite
                        self[i][-1] = range[0] - 1
                    i += 1
        self.cleanup()
        return True
                            
class Overview:
    """Contient l'overview d'un newsgroup"""
    def __init__(self, name, server):
        self.name = name
        self.server = server
        self.cached = ArticleRange([])
        self.data = {}

    def get_item(self, number):
        debug_output('[%s::get_item] Asked to get %d'
                     % (self.name, number))
        
        if number not in self.cached:            
            self.add_data(number, number)
        if number in self.data:
            return self.data[number]
        else:
            return None
            
    def get_overview(self, start, end):
        # Cas grotesques
        if end < start: start, end = end, start
        
        debug_output('[%s::get_overview] Asked to get %d-%d'
                     % (self.name, start, end))
        to_dl = ArticleRange([start, end])
        for r in self.cached: to_dl.del_range(r)
        for r in to_dl:
            self.add_data(r[0], r[1])
        result = []
        vanished = []

        first, last = self.server.group_stats(self.name)
        for i in xrange(max(first, start), min(last, end) + 1):
            if i in self.data:
                result.append(self.data[i])
            else:
                vanished.append(i)
        return (result, vanished)
    
    def add_data(self, start, end):
        debug_output('[%s::add_data] Downloading %d-%d'
                     % (self.name, start, end))
        things, real_range = self.server.overview(self.name, start, end)
        # On indique ce qu'on a téléchargé, ou au moins demandé (si on
        # les a pas eus, inutile de redemander)
        self.cached.add_range(real_range)

        # On ajoute les nouvelles données
        for i in things:
            self.data[int(i[0])] = i
        
