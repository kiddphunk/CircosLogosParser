# PoemParser 0.5
# (c) 2010-2011 Ian Timourian @ [beatspixelscodelife.com](beatspixelscodelife.com)
#
# PoemParser is freely distributable under the MIT license.
#
# See also:
#
# [visual poetry, part 1 / audioizing gertrude stein](http://beatspixelscodelife.com/projects/2011/10/03/visual-poetry-part-one-audioizing-gertrude-stein/)
# 
# [github.com/kiddphunk/VisualPoetry](https://github.com/kiddphunk/VisualPoetry)
# 

# Imports
# -------

from curses.ascii import isdigit 
from random import *
import string
import getopt
import sys

# [Natural Language Toolkit (NLTK)](http://www.nltk.org) for
# language / poem analysis.
import nltk
from nltk import Nonterminal, nonterminals, Production, parse_cfg, ContextFreeGrammar, FreqDist
from nltk.corpus import cmudict
from nltk.collocations import *
from nltk.util import *
from nltk.tokenize import WhitespaceTokenizer

# [EchoNest Remix API](http://code.google.com/p/echo-nest-remix/) for
# programmatic MIDI music synthesis.
from midi.MidiOutFile import MidiOutFile



#
class PoemParser():

  #
  def __init__(self, dataset="picasso2", basedir="parsed_data"):
    self.dataset = dataset
    self.basedir = basedir
    filename = "%s/%s/source/%s" % (basedir,dataset,dataset)
    self.debug("poemparser:init:dataset parsing '%s'..." % filename)

    with open("pyParser/english_words.txt") as word_file:
      self.english_words = set(word.strip().lower() for word in word_file)

    # Open and analyze the text data.
    self.unknownWords   = {}
    self.iffyWords      = {}
    self.allmatch       = {}
    self.alltokens      = self.openTokens(filename)
    self.parsedTokens   = [token for token in self.alltokens[0] if token != '-']
    self.replacedTokens = [token for token in self.alltokens[1] if token != '-']
    self.fullTokens     = [token for token in self.alltokens[2] if token != '-']
    self.tokens         = self.parsedTokens
    self.loweredTokens  = [token.lower() for token in self.replacedTokens]
    self.pos_tags       = nltk.pos_tag(self.replacedTokens)
    self.text           = nltk.Text(self.tokens)
    self.dict           = cmudict.dict() 
    self.lastspeed      = 0
    self.midiindex      = 0
    
    self.setMIDISettings(12)
    
    self.debug("poemparser:init:words %s"  % self.fullTokens)
    self.debug("poemparser:init:tokens %s" % self.tokens)
    self.debug("poemparser:init:text %s"   % self.text)
 
  #
  def runAll(self):
    # Print interesting NLTK data.
    self.printAllNgrams()
    self.printAllConcordance()
    self.generatePseudoText(300)   

    tempo = 125000

    # Render MIDI files.
    self.createMIDIFile('%s70.mid'  % self.dataset, 70,  tempo)
    self.createMIDIFile('%s100.mid' % self.dataset, 100, tempo)
    self.createMIDIFile('%s130.mid' % self.dataset, 130, tempo)
    
    self.createMIDIFile('%s30_abs.mid'  % self.dataset, 30,  tempo, True)
    self.createMIDIFile('%s90_abs.mid'  % self.dataset, 90,  tempo, True)
    self.createMIDIFile('%s120_abs.mid' % self.dataset, 120, tempo, True)


    if False:
      self.createMIDIFile('%s30.mid'  % self.dataset, 30,  tempo) 
      self.createMIDIFile('%s90.mid'  % self.dataset, 90,  tempo)
      self.createMIDIFile('%s120.mid' % self.dataset, 120, tempo)
      self.createMIDIFile('%s70_abs.mid'  % self.dataset, 70,  tempo, True)
      self.createMIDIFile('%s100_abs.mid' % self.dataset, 100, tempo, True)
      self.createMIDIFile('%s130_abs.mid' % self.dataset, 130, tempo, True)

    # Generate JSON datafile.
    self.generateJSON(70)

    for s in sorted(self.unknownWords.keys()):
      self.debug("Iffy word: (BAD!) [ %s (%s) ]"%(s, self.unknownWords[s]), '')
    for s in sorted(self.iffyWords.keys()):
      self.debug("Iffy word:        [ %s (%s) ]"%(s, self.iffyWords[s]), '')


  #
  def createMIDIFile(self, filename, startnote, tempo=250000, absoluteIndexing=False):
    self.debug("poemparser:createMIDIFile:filename %s"%filename)
    self.__midistart(filename)

    self.pos_tag_iter = (pos for (word, pos) in self.pos_tags)

    for i, token in enumerate(self.parsedTokens):
      if i > 0:
        lastword = self.fullTokens[i-1]
        self.__midiadd(i, token, lastword, startnote, absoluteIndexing)
      else:
        self.__midiadd(i, token, None, startnote, absoluteIndexing)

    self.__midiend()


  # Output Configuration Settings
  # -----------------------------
  def setMIDISettings(self, version=12):
    if version == 1:
      self.settings = {

        # `......v---------<range>--------v.............`
        # `||2C||||||3C||||||4C||||||...||||||7C|||||||| <- all notes`
        # `......^................^.....................`
        #
        # `......^...............<startnote>............`
        #
        # `.....<offset>................................`

        # `startnote` - The MIDI note to map to the first word in the poem.
        'startnote':70, 

        # `range` - The spectrum/number of musical notes in our vocabulary.
        'range':127, 

        # `offset` - The bottom offset of the MIDI spectrum.
        'offset':0, 

        # `numchannels` - The number of channels.
        'numchannels':9, 

        # `1==short`, `2==short_and_long`, `>2==mod_by`
        'truncate':0,

        #
        'randdist':50, 

        #
        'randoffset':50, 

        # The default loudness level.
        'loudness':0x64, 

        # The direction of musical / poem progression.
        'direction':'up', 

        # Should we include the MIDI drum channel?
        'drums':True,

        # The name of this session / configuration.
        'name':'v0', 

        # The algorithm to use in conjunction with these settings.
        'algo':1 }

    # **"Experimental" settings**
    if version == 2:
      self.settings = {'startnote':70, 'range':127, 'offset':0, 'numchannels':9, 'truncate':0,
                              'randdist':50, 'randoffset':50, 'loudness':0x64, 'direction':'down', 
                              'drums':True, 'name':'v1', 'algo':1}
    if version == 3:
      self.settings = {'startnote':20, 'range':127, 'offset':0, 'numchannels':9, 'truncate':0,
                              'randdist':50, 'randoffset':50, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v2', 'algo':2}
    if version == 4:
      self.settings = {'startnote':20, 'range':127, 'offset':0, 'numchannels':9, 'truncate':10,
                              'randdist':50, 'randoffset':50, 'loudness':0x64, 'direction':'down', 
                              'drums':False,'name':'v4', 'algo':3}
    if version == 5:
      self.settings = {'startnote':20, 'range':127, 'offset':0, 'numchannels':9, 'truncate':10,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v5', 'algo':3}
    if version == 6:
      self.settings = {'startnote':40, 'range':84, 'offset':0, 'numchannels':9, 'truncate':10,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v6', 'algo':4}
    if version == 7:
      self.settings = {'startnote':20, 'range':108, 'offset':0, 'numchannels':9, 'truncate':10,
                              'randdist':35, 'randoffset':35, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v7', 'algo':3}
    if version == 8:
      self.settings = {'startnote':20, 'range':108, 'offset':0, 'numchannels':9, 'truncate':10,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v8', 'algo':4}
    if version == 9:
      self.settings = {'startnote':20, 'range':108, 'offset':0, 'numchannels':9, 'truncate':2,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v9', 'algo':5}
    if version == 10:
      self.settings = {'startnote':20, 'range':108, 'offset':0, 'numchannels':9, 'truncate':2,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v10', 'algo':4}
                              
    # **"Production" settings**
    if version == 11:
      self.settings = {'startnote':20, 'range':96, 'offset':12, 'numchannels':9, 'truncate':2,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v11', 'algo':7}
    if version == 12:
      self.settings = {'startnote':12, 'range':72, 'offset':24, 'numchannels':9, 'truncate':10,
                              'randdist':15, 'randoffset':45, 'loudness':0x64, 'direction':'down', 
                              'drums':False, 'name':'v12', 'algo':4}
    if version == 0: # bass
      self.settings = {'startnote':20, 'range':30, 'offset':10, 'numchannels':1, 'truncate':2,
                              'randdist':50, 'randoffset':50, 'loudness':0x64, 'direction':'down',
                              'drums':False, 'name':'bass', 'algo':2}



  # Helper methods
  # --------------

  # Returns a random amount of 'jigger' (up to 10ms) 
  # to 'de-robotise' and avoid any patterns that sound overly precise 
  # and inhuman.
  def addTimeToHumanize(self):
    return int(random()*10)


  # Returns a length of time determined by the number of syllables in the word.
  def addTimeForSyllables(self, word):
    return (self.numsyl(word)[0]-1)*100


  # **ISSUE** - *these next two methods are crude and can obviously have 
  # false positives (e.g. "St. Elmo's Fire") but for the poem it was 
  # created they are sufficient.*
  
  
  # Returns a random length of time (100ms - 500ms) if a period is found.
  def addTimeForSentenceEnd(self, lastfullword):
    try:
      if lastfullword.find('.') != -1:
        return int(random()*400)+100
    except:
      pass              
    return 0


  # Returns a random length of time (80ms - 380ms) if a comma is found.
  def addTimeForSentencePause(self, lastfullword, span=300, off=80):
    try:
      if lastfullword.find(',') != -1:
        return int(random()*span)+off
    except:
      pass              
    return 0


  # Returns a loudness metric based on the word count; the more frequently
  # a word is used, the louder it will become.
  def addLoudnessForCount(self, count, boost=0):
    try:
      return self.settings['loudness']-40+2*count+boost
    except:
      pass              
    return 0


  # Returns the resolved note index for the current `word`.
  def getNoteIndex(self, absindex, word, startnote):
    i = self.midiwordinfo[word][1]
    
    # Are we progressing up the scale or down?
    if self.settings['direction'] == 'up':
      self.debug("----> note = %s" % ((startnote+i)%self.settings['range']+self.settings['offset']))
      return (startnote+i)%self.settings['range']+self.settings['offset']  
    else:
      self.debug("----> note = %s" % ((startnote-i)%self.settings['range']+self.settings['offset']))
      return (startnote-i)%self.settings['range']+self.settings['offset']


  # Music Generation Algorithms
  # ---------------------------

  def getAlgoFunc(self, algo):
    return {
      1:self.__algo1,
      2:self.__algo2,
      3:self.__algo3,
      4:self.__algo4,
      5:self.__algo5,
      7:self.__algo7,
    }[algo]


  # **Algorithm 1**
  def __algo1(self, index, word, lastfullword, startnote, just_index=False):
    noteindex = self.getNoteIndex(None, word, startnote)

    if just_index:
      return noteindex

    self.midi.note_on(index%self.settings['numchannels'], noteindex, self.settings['loudness'])
    self.midi.update_time(int(random()*self.settings['randdist']+self.settings['randoffset']))

    return noteindex


  # **Algorithm 2**
  def __algo2(self, index, word, lastfullword, startnote, just_index=False):
    noteindex = self.getNoteIndex(None, word, startnote)
    if just_index:
      return noteindex
    
    extratime = self.addTimeForSentenceEnd(lastfullword)
      
    self.midi.note_on(index%(self.settings['numchannels']), noteindex, self.settings['loudness'])
    self.midi.update_time(int(random()*self.settings['randdist']+self.settings['randoffset']+extratime))
    
    # *Short notes*
    if self.settings['truncate'] == 1:
      self.midi.note_off(index%self.settings['numchannels'], noteindex)
      
    # *Short and long notes*
    if self.settings['truncate'] == 2:
      if random() < .5:
        self.midi.note_off(index%self.settings['numchannels'], noteindex)

    return noteindex


  # **Algorithm 3**
  def __algo3(self, index, word, lastfullword, startnote, count=0, just_index=False):
    noteindex = self.getNoteIndex(None, word, startnote)
    if just_index:
      return noteindex
    
    extratime = self.addTimeForSentenceEnd(lastfullword) + \
                self.addTimeForSentencePause(lastfullword) + \
                self.addTimeForSyllables(word)    
    loudness =  self.addLoudnessForCount(count)

    self.midi.note_on(index%(self.settings['numchannels']), noteindex, loudness)
    self.midi.update_time(int(random()*self.settings['randdist']+self.settings['randoffset']+extratime))
    
    # *Short and long based on index*
    if self.settings['truncate']:
      if (count % self.settings['truncate']):      
        self.midi.note_off(index%self.settings['numchannels'], noteindex)
        self.midi.update_time(0)
    return noteindex


  # **Algorithm 4 base**
  def __algo4_base(self, index, word, lastfullword, startnote, noteindex, count=0, just_index=False): 
    extratime = 0
    extraloud = 0    
    try:
      extratime = self.addTimeForSentenceEnd(lastfullword)
      if extratime > 0:
        extraloud = 15
        self.lastspeed = int(random()*self.settings['randdist']+self.settings['randoffset'])        

      extratime = self.addTimeForSentencePause(lastfullword, 150, 100)
      if extratime > 0:
        extraloud = 10
        self.lastspeed = int(random()*self.settings['randdist']+self.settings['randoffset'])
    except:
      pass      
    extratime += self.addTimeForSyllables(word) + \
                 self.addTimeToHumanize()
    loudness   = self.addLoudnessForCount(count, extraloud)

    if loudness > 255:
      loudness = 255

    self.midi.note_on(index%(self.settings['numchannels']), noteindex, loudness)
    self.midi.update_time(self.lastspeed+extratime)

    # *Short and long based on index*
    if self.settings['truncate']:
      if (count % self.settings['truncate']):      
        self.midi.note_off(index%self.settings['numchannels'], noteindex)
        self.midi.update_time(0)
    return noteindex



  # **Algorithm 4**
  def __algo4(self, index, word, lastfullword, startnote, count=0, just_index=False):    
    noteindex = self.getNoteIndex(None, word, startnote)
    if just_index:
      return noteindex
    return self.__algo4_base(index, word, lastfullword, startnote, noteindex, count, just_index)



  # **Algorithm 5**
  def __algo5(self, index, word, lastfullword, startnote, count=0, just_index=False):    
    return self.__algo4(index, word, None, startnote, count=0, just_index=False)
    
    

  # **Algorithm 7**
  def __algo7(self, index, word, lastfullword, startnote, count=0, just_index=False):    
    noteindex = self.getNoteIndex(1, word, startnote)
    if just_index:
      return noteindex
    return self.__algo4_base(index, word, lastfullword, startnote, noteindex, count, just_index)


  # MIDI Generation
  # ---------------

  # Initialize the MIDI generator, creating the output MIDI file and header info.
  def __midistart(self, filename, tempo=250000):
    dir = "%s/%s/songs"%(self.basedir, self.dataset)
    if not os.path.exists(dir):
      os.makedirs(dir)

    name = self.settings['name']
    algo = self.settings['algo']
    self.midiindex = 0
    self.midiwordinfo = {}
    self.midiwordinfo['_firsttime'] = True
    self.midi = MidiOutFile("%s/a%s_%s_%s"%(dir, algo, name.replace(' ','_'), filename))
    self.debug("Creating MIDI file ------------------")
    self.midi.header()
    self.midi.start_of_track() 
    self.midi.tempo(tempo)
    self.midi.time_signature(4, 2, 24, 8)


  # Outputs the next MIDI note for the current word.   
  def __midiadd(self, index, word, lastfullword, startnote=0, absoluteIndexing=False):
    try:
      if self.midiwordinfo[word][0] > 0:    
        pass
        
    except:
      self.midiindex += 1
      self.midiwordinfo[word] = {}
      self.midiwordinfo[word][0] = 0
      
      if absoluteIndexing:
        self.midiwordinfo[word][1] = self.midiindex
      else:
        self.midiwordinfo[word][1] = index+1 

    if not startnote:
      startnote = self.settings['startnote']

    self.midiwordinfo[word][0] += 1

    # This is where the real logic lies, in the various alorithms that determine the
    # individuality of this note/musical phrase.
    noteindex = self.getAlgoFunc(self.settings['algo'])(index, word, 
        lastfullword, startnote, self.midiwordinfo[word][0])
    
    if self.midiwordinfo['_firsttime']:
      self.debug("poemparser:__midiadd %s %s . %s . %s . %s . %s\n" %
        ("word" .rjust(30),
         "idx"  .rjust(4),
         "cnt"  .rjust(3),
         "midi" .rjust(4),
         "pos"  .rjust(5),
         "syl"  .rjust(3)), '')
      self.midiwordinfo['_firsttime'] = 0
    
    self.debug("poemparser:__midiadd %s %s . %s . %s . %s . %s" %
      (("%s" % word)                        .rjust(30),
       ("%s" % index)                       .rjust(4),
       ("%s" % self.midiwordinfo[word][0])  .rjust(3),
       ("%s" % noteindex)                   .rjust(4),
       ("%s" % self.pos_tag_iter.next())    .rjust(5),
       ("%s" % self.numsyl(word))           .rjust(3)), '')
  

  # Finalize the MIDI generation.
  def __midiend(self):
    self.midi.update_time(0)
    self.midi.end_of_track()
    self.midi.eof()


  # NLTK Parsing and Analysis
  # -------------------------

  def is_english_word(self,   word):
    return word.lower() in self.english_words
  
  #
  def openTokens(self, filename):
    words = open(filename).read()

    # This is a clunky and kludgy data cleaning step; however, it really 
    # depends upon the source material, so I just put in some default 
    # logic that should work in most cases.
    tokenizedWords = WhitespaceTokenizer().tokenize(words)
    sanitizedWords = []
    replacedWords  = []
    for word in tokenizedWords:
      self.debug("ORIGINAL WORD %s"%word, '')

      str   = u'[().,!;?"]'
      reg   = re.compile(str)
      word  = reg.sub('',  word)
      rword = word
      lword = False

      if len(word) > 1:
        if word[len(word)-1] == "'" and word[0] == "'":
          word = word.replace("'",'')

        # Remap *in' -> *ing
        if (word[len(word)-1] == "'") and (len(word) > 2) and (word[len(word)-2] == "n") and (word[len(word)-3] == "i"):
          lword = word
          rword = word[:len(word)-1]+'g'
          self.debug("ADJUSTED WORD %s"%rword, '')

        elif word[len(word)-1] == "'":
          word = word[:len(word)-1]

        if word[0] == "'":
          word = word[1:]

        # Maybe this is useful to make an option, dunno. 
        if False:
          if word[len(word)-2] == "'" and word[len(word)-1] == "s":
            word = word.replace("'s",'')

        # Todo:... Figure out how to get the encoding working here.
        if False:
          str  = u'[().,!;?"\u0091\u0092\u0093\u0094]'.encode('iso-8859-1')
          reg  = re.compile(str)
          word = word.decode('iso-8859-1')
          word = word.translate(string.maketrans('\x91','\''),'')
          word = word.translate(string.maketrans('\x92','\''),'')
          word = word.translate(string.maketrans('\x93','"'),'')
          word = word.translate(string.maketrans('\x94','"'),'')
          word = reg.sub('', word)

      if word != '':
        sanitizedWords.append(word)
        replacedWords.append(rword)

        if not self.is_english_word(rword):
          index = lword or rword
          # Ignore contractions.
          if rword.find('\'') != -1:
            try:
              self.iffyWords[index] += 1
            except:
              self.iffyWords[index]  = 1
          else:
            try:
              self.unknownWords[index] += 1
            except:
              self.unknownWords[index ] = 1
          
    return [sanitizedWords, replacedWords, words.split()]



  # Returns the number of syllables in the word.
  def numsyl(self, word): 
    try:
      return [len(list(y for y in x if isdigit(y[-1]))) for x in self.dict[word.lower()]]
    except:
      return [0]



  # Returns all nGrams of length `len`.
  def ngramFinder(self, len):
    match = {}

    for n in ngrams(self.loweredTokens, len):    
      a = tuple(n)
      self.debug(a)
      try:
        self.allmatch[a] = match[a] = match[a]+1
      except:
        self.allmatch[a] = match[a] = 1

    for s in sorted(match.keys(), key=lambda m: match[m], reverse=True):
      if match[s] > 1:
        self.debug("poemparser:ngramFinder %s : %s"%(match[s], s), '')

    return match



  # Ideally, this method would find all rhymes, although I am not 100%
  # sure how to tackle this one yet... saving for later.
  # See [this paper](http://www.mit.edu/~6.863/spring2011/nltk/ch2-3.pdf) for more details.
  def rhymeFinder(self):
    tokenHash = {}
    for word in self.tokens:
      tokenHash[word] = None

    entries = nltk.corpus.cmudict.entries()
    for word in entries:
      if tokenHash[word[0]]:
        tokenHash[word[0]] = word[1]



  # Utilizes NLTK's pseudo-text generation ability to create text in 
  # a similar style as the source text.
  def generatePseudoText(self, textlen=100):
    self.debug("poemparser:generatePseudoText \n")
    self.text.generate(textlen)



  # Generate a JSON data file containing the statistics for the words
  # in the source file. Will be consumed by JS-visualization programs.
  def generateJSON(self, startnote, varname=None):
    self.pos_tag_iter = (pos for (w, pos) in self.pos_tags)

    if not varname:
      varname = self.dataset

    js = ''
    found = 0
    lastfullword = None
    self.midiwordinfo = {}

    for i, word in enumerate(self.parsedTokens):
      try:
        mwi = self.midiwordinfo[word]
        if mwi[0] > 0:    
          pass
      except:     
        found += 1
        mwi = self.midiwordinfo[word] = {}
        mwi[0] = 0
        mwi[1] = found
        
      noteindex = self.getAlgoFunc(self.settings['algo'])(i, word, lastfullword, startnote, mwi[0], True)
      mwi[0] += 1
      js += ('{"word": "%s", "rword": "%s", "fullword": "%s", "index": "%s", "count": "%s", "wordindex": "%s",\
               "noteindex": "%s", "numsyl": "%s", "pos": "%s"},\n' %
        (self.parsedTokens[i], self.replacedTokens[i], self.fullTokens[i].replace("\"","\\\""), mwi[1]+1, mwi[0], i+1,
         noteindex, self.numsyl(word)[0], self.pos_tag_iter.next()))

      lastfullword = word

    js = '[\n%s\n]'%(js[:-2])
    self.debug("poemparser:generateJSON \n%s\n"%js)    
    self.dumpfile('javascript', "%s.json"%self.dataset, js)
    
    ngramJSON = '[\n%s\n]' % self.printSortedNgrams(True)
    self.dumpfile('javascript', "%s_ngrams.json"%self.dataset, ngramJSON)

    return js



  #
  def printAllNgrams(self):
    for n in range(2, 20):
      self.debug("poemparser:printAllNgrams ----------------- %s ----------------\n"%n)
      ng = self.ngramFinder(n)
      self.printSortedNgrams()


  #
  def printSortedNgrams(self, returnJSON=False):
    ret = ''
    for s in sorted(self.allmatch.keys(), key=lambda m: self.allmatch[m], reverse=True):
      if self.allmatch[s] > 1:
        if returnJSON:
          words = ", ".join(["\"%s\"" % w for w in s])
          ret += "{\"count\":%s,\"words\" : [%s]},\n" % (self.allmatch[s], words)
        else:
          self.debug("poemparser:printAllNgrams %s : %s"%(self.allmatch[s], s), '')
    return ret[:-2]


  #
  def printAllConcordance(self):
    for word in sorted(set(self.tokens).difference([".", ",", "!", "?", ";", ":", "-"])):
      cc = self.get_concordance(word)
      self.debug("poemparser:printAllConcordance ----------------- %s ----------------\n%s\n"%(word,cc))
      if args['concord']:
        self.dumpfile('concordances', word, cc)



  # Pretty-parsing for concordance output.
  def get_concordance(self, word, width=75, lines=25): 
    half_width = (width - len(word) - 2) / 2 
    # Approximate number of words of context.
    context = width/4 
    ret = ''
    self.text.concordance(word)

    offsets = self.text._concordance_index.offsets(word) 
    if offsets: 
      lines = min(lines, len(offsets)) 

      for i in offsets: 
        if lines <= 0: 
          break 

        left  = (' ' * half_width + ' '.join(self.text._concordance_index._tokens[i-context:i])) 
        right = ' '.join(self.text._concordance_index._tokens[i+1:i+context]) 
        left  = left[-half_width:] 
        right = right[:half_width] 
        ret  += "%s  %s  %s\n"%(left, word, right)

        lines -= 1 

    else: 
      pass  
    return ret


  # Create/open/dump data.
  def dumpfile(self, module, filename, msg):
    dir = "%s/%s/%s"%(self.basedir, self.dataset, module)
    if not os.path.exists(dir):
      os.makedirs(dir)
    if generate_files:
      f = open("%s/%s"%(dir,filename), 'w')
      f.write(msg)
      f.close()

  # 
  def debug(self, msg, prefix="\n\n"):
    if args['verbose']:
      print "%s%s"%(prefix,msg)


# Main
# ----

args = {'dataset':'picasso', 'verbose':False, 'concord':False}
if __name__ == '__main__':
  try:
    opts, _args = getopt.getopt(sys.argv[1:], "d:v", ["dataset="])
  except getopt.GetoptError, err:
    print str(err)
    print "Usage: python parser.py -v --concord --dataset 'greeneggs'"
    sys.exit(2)

  for o, a in opts:
    if o == "-v":
      args['verbose'] = True
    elif o in ("--concord"):
      args['concord'] = True
    elif o in ("-d", "--dataset"):
      args['dataset'] = a        

  generate_files = True
  pp = PoemParser(dataset=args['dataset'])
  pp.runAll()

