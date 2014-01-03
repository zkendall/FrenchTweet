#!/home/syszachariah/env/bin/python
#-------------------------------------------------------------------------------
# Name:        ExampleScraper
# Purpose:     Get good example sentences of French words.
# Author:      ZKendall
# Notes:
#-------------------------------------------------------------------------------

#---------------------------------------
#           Includes
#---------------------------------------

# Scraper
import urllib2
from lxml import etree
import StringIO
from lxml.html import fromstring, tostring
# Database
from peewee import *
# Twitter
from twython import Twython
import os
# Main
import time

#---------------------------------------
#           Scraper
#---------------------------------------
header = { 'User-Agent' : 'Mozilla/5.0' }
url = "http://www.wordreference.com/fren/"

def get_examples(word):
    """ Scrapes example french sentences from WordReference.com """
    req = urllib2.Request(
        url + word,
        None,
        header)
    content = StringIO.StringIO(urllib2.urlopen(req).read())

    parser = etree.HTMLParser()
    tree = etree.parse(content, parser)

    xpath = "//td[@class='FrEx']"
    res = tree.xpath(xpath)

    examples = [word]
    for ex in res:
        examples.append(ex.text.encode("utf-8"))

    return examples

def _get_words(fin):
    """ Generator: yields words from file 'fin' """
    with open(fin, 'r') as f:
        for word in f:
            yield word.strip()


#---------------------------------------
#           Database
#---------------------------------------
db = SqliteDatabase('examples.db')

def initDb():
    '''Create ALL the tables'''
    print "Initializing database"
    Word.create_table(True)
    Example.create_table(True)
    KeyValue.create_table(True)
    print "Finished initializing database"

def save_words(fin):
    """ Put words from file into db """
    print "Loading word file into db"
    # Get existing for duplicate check
    existing = Word.select(Word.word)
    wordList = []
    for w in existing:
        wordList.append(w.word)

    for new_word in _get_words(fin):
        try:
            w = Word.get(Word.word==new_word)
        except Word.DoesNotExist, e:
            print "Adding", new_word
            Word.create(word=new_word, retrieved=False)

def get_save_examples(word):
    """ Get examples and put in db """
    for e in get_examples(word):
        foreignKey = Word.get(Word.word == word).id
        length = len(e)
        Example.create(word=foreignKey,
                       sentence=e,
                       length=length
                       )

class BaseModel(Model):
    class Meta:
        database = db

class Word(BaseModel):
    """This table holds words"""
    word = CharField()
    retrieved = BooleanField(default=False)

class Example(BaseModel):
    """This table holds example sentences"""
    word = ForeignKeyField(Word, related_name='examples')
    sentence = CharField()
    length = IntegerField()
    used = BooleanField(default=False)

class KeyValue(BaseModel):
    """Table to hold assorted things like twitter authentication"""
    key = CharField()
    value = CharField()


#---------------------------------------
#           Twitter
#---------------------------------------
def authTwit():
    APP_KEY = os.environ.get('TWITTER_APP_KEY')
    APP_SECRET = os.environ.get('TWITTER_APP_SECRET')
    OAUTH_TOKEN = os.environ.get('TWITTER_OAUTH_TOKEN')
    OAUTH_TOKEN_SECRET = os.environ.get('TWITTER_OAUTH_TOKEN_SECRET')
    print APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
    return Twython(APP_KEY, APP_SECRET,
                   OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

twit = None
def update_status(example):
    """ Send text to twitter account to tweet """
    msg = example.sentence.encode('utf-8')
    print "Tweeting: " + msg
    twit = authTwit()
    try:
        twit.update_status(status=msg)
    except Exception, e:
        print "Recieved error: ", e
        print "Marking example used to move on."
        example.used = True



#---------------------------------------
#           Main
#---------------------------------------
def main():
    print "Starting..."

    initDb()
    save_words("common_words.txt")

    while(1):
        try:
            example = getExample()
        # No unused examples
        except Example.DoesNotExist:
            # Get word from db
            w = Word.get(Word.retrieved==False)
            # Scrap examples
            get_save_examples(w.word.encode('utf-8'))
            # Mark word scrapped
            w.retrieved = True
            w.save()
            example = getExample()

        # Tweet example
        update_status(example)
        # Mark example used
        example.used = True
        example.save()

        # Time out
        print "Pausing for 6 hours..."
        time.sleep(21600)
        print "Resuming..."

def getExample():
    """Just a little helper method to clean up code"""
    return Example.get(Example.used==False
                    , Example.length < 144
                    , Example.length > 10
            )

if __name__ == '__main__':
    main()
