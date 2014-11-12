# -*- coding: UTF-8 -*-
import requests
import json
import gensim.corpora.wikicorpus as wikicorpus
from gensim.models import LdaModel
from gensim import corpora
from operator import itemgetter
import wikipedia
import re
import os
import geoip2.database
import irc.bot
import datetime
from MeteorClient import MeteorClient
import logging
import logging.handlers

#--------------------------------------------------------#
#                       Set up logging                   #
#--------------------------------------------------------#

f = logging.Formatter(fmt='%(asctime)s; %(levelname)s:%(name)s: %(message)s '
                      ' %(filename)s:%(lineno)d',
                      datefmt="%Y-%m-%d %H:%M:%S")
handlers = [
    logging.handlers.RotatingFileHandler('server.log', encoding='utf8',
                                         maxBytes=100000, backupCount=1),
    # logging.StreamHandler()
]
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
for h in handlers:
    h.setFormatter(f)
    h.setLevel(logging.DEBUG)
    root_logger.addHandler(h)


#--------------------------------------------------------#
#                       Load models                      #
#--------------------------------------------------------#

topic_names = {0: "Society and social sciences",
               1: "Technology and Science",
               2: "Music",
               3: "Sports",
               4: "East Europe",
               5: "Economy and Business",
               6: "Culture and the arts",
               7: "Nature and physical sciences",
               8: "Movies, Television",
               9: "Geography and Places",
               10: "History",
               11: "Politics",
               12: "Games and Stories",
               13: "Education and Research",
               14: "USA",
               15: "Social Sciences , Religion and Literature",
               16: "Europe",
               17: "Military and War",
               18: "Africa, India and Middle East",
               19: "Asia",
               20: "Great Britain",
               21: "Technology and Science"}


DATADIR = 'models/'
id2word = corpora.Dictionary.load_from_text(
    os.path.join(DATADIR, 'wiki_wordids.txt.bz2'))
lda_model = LdaModel.load(os.path.join(DATADIR, 'lda_model'))
geoip_reader = geoip2.database.Reader(
    os.path.join(DATADIR, 'GeoLite2-Country.mmdb'))
wikipedia.set_user_agent(
    'EditsGeoVisualization/1.0 (http://yasermartinez.com; yaser.martinez@gmail.com)')

logging.info("Loaded models")


#--------------------------------------------------------#
#                       Helpers                          #
#--------------------------------------------------------#
def wiki_bow(title):
    """This function downloads text from Wikipedia

    Parameters
    ----------
    title: string
        The title of the article

    Returns
    -------
    content: string
        The raw text of the article

    summary: string
        The summary of the article

    url: string
        The link to the article

    If there is some IO error or the title is not found all outputs are None
    """

    try:
        page = wikipedia.page(title)
    except:
        return None, None, None
    return page.content, page.summary, page.url


def get_topic(text, id2word=id2word, lda_model=lda_model, topic_names=topic_names):
    """Given a document (in list of tokens form) chose the closest topic

    Parameters
    ----------
    text: string
        The text to be analized

    id2word: gensim.corpora.dictionary.Dictionary
        A gensim Dictionary

    lda_model: gensim.models.ldamodel.LdaModel
        A gensim LDA model

    topic_names: dict
        A topic(int) -> topic name(str)` mapping
        Example:
            {0: "Society and social sciences",
             1: "Technology and Science",
             2: "Music"}
    """
    doc, _, _ = wikicorpus.process_article([text, False, '', 0])
    doc_bow = id2word.doc2bow(doc)
    topic = max(lda_model[doc_bow], key=itemgetter(1))[0]
    return topic_names.get(topic)


def is_valid_ipv4(ip):
    """Validates IPv4 addresses.

    Note: Regex validation works better for this use case as sometimes
    Wikipedia returns number like `452` which are valid IP addresses
    """

    pattern = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    return pattern.match(ip) is not None


def get_location(ip_addr, reader=geoip_reader):
    """Geolocates an IP address using an offline geoip2 database

    Parameters
    ----------

    ip_addr: string
        The IP address.

    reader: geoip2.database.Reader
        A geoip2 db reader object
    """
    try:
        response = reader.country(ip_addr)
        return response.country.name, response.country.iso_code
    except:
        return ''


def dthandler(obj):
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return obj.isoformat()
    else:
        return None


def update_values(item, collection='piedata', field='value'):
    """Increases in 1 the value of field for the corresponding item or topic

    Parameters
    ----------

    item: string
        This item will have its corresponding `value` increased by one

    collection: string
        The Meteor Collection that is being updated

    field: string
        The field in the collection being updated
    """
    logging.debug("Updating %s in %s", item, collection)
    doc = client.find_one(collection, {'label': item})
    if doc is None:
        # insert new value
        client.insert(collection, {'label': item,
                                   'value': 1})
    else:
        client.update(
            collection, {'_id': doc.get('_id')}, {'$inc': {field: 1}})


def parse_irc_message(msg):
    """Parses a Wikipedia IRC formatted message

    Returns
    -------
    title: string
        The title of the article being edited
    ip: string
        The extracted ip address of the originating edit
    """

    s = msg.arguments[0]
    pattern = r'\x0307(.*)\x0314.*\x0303(.*)\x03 \x035'
    parsed = re.search(pattern, s)
    title = parsed.group(1)
    ip = parsed.group(2)
    return title, ip


# def wikimedia_geotagging(title):
#     title = 'Asian Art Museum of San Francisco'
#     headers = {'User-Agent': ('EditsGeoVisualization/1.0'
#                               '(http://yasermartinez.com; yaser.martinez@gmail.com)')}
#     url = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=coordinates&titles={title}&coprop=dim|country&continue=&colimit=10&callback=?".replace(
#         '{title}', title)
#     r = requests.get(url)
#     return json.loads(r.content.lstrip('/**/(').rstrip(')'))


class WikiBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, nickname, server, port):
        irc.bot.SingleServerIRCBot.__init__(
            self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_nicknameinuse(self, c, e):
        logging.info("Nickname in use. Adding _")
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        logging.info("Joining channel ...")
        c.join(self.channel)
        logging.info("Joined")

    def on_pubmsg(self, c, e):
        title, ip = parse_irc_message(e)
        logging.debug("New doc with title: %s", title)
        if title.startswith('Special:'):
            logging.debug("Skipped")
            return

        if is_valid_ipv4(ip):
            msg = dict()
            msg['ip'] = ip
            logging.debug("Adding IP: %s", ip)
            msg['title'] = title
            # insert timestamp
            msg['createdAt'] = json.dumps(
                datetime.datetime.now(), default=dthandler)

            # geolocate ip
            country, iso_code = get_location(ip)
            if country:
                # patch of shame
                if country == "United States":
                    country = "the United States"
                msg['country'] = country
                msg['iso_code'] = iso_code.lower()
                logging.debug("Geolocated country %s(%s). Updating piedata...",
                              country, iso_code)
                update_values(iso_code, 'piedata')

            # calculate topics
            doc, summary, url = wiki_bow(title)
            if doc:
                msg['url'] = url
                msg['summary'] = summary
                msg['short_summary'] = summary[:250] + '...'
                topic = get_topic(doc)
                msg['topics'] = topic
                logging.debug("Topic %s. Updating bardata values...", topic)
                update_values(topic, 'bardata')
            else:
                msg['url'] = ""
                msg['summary'] = "Not available"
                msg['short_summary'] = "Not available"
                msg['topics'] = "Not available"

            logging.debug("Updating Edits with message %s", msg)
            client.insert('edits', msg)

#--------------------------------------------------------#
#                       Main                             #
#--------------------------------------------------------#
if __name__ == "__main__":

    # Connect to meteor server
    ws = "ws://ddp--8162-wikiedits.meteor.com/websocket"
    #ws = "ws://127.0.0.1:3000/websocket"
    logging.info("Connecting to meteor server")
    client = MeteorClient(ws, auto_reconnect=True, auto_reconnect_timeout=10)
    client.connect()
    client.subscribe('piedata')
    client.subscribe('edits')
    client.subscribe('bardata')
    logging.info("Connected")

    logging.info("Starting IRC server")
    # Start Wikipedia bot
    server = 'irc.wikimedia.org'
    port = 6667
    nickname = 'elyasebot'
    channel = '#en.wikipedia'
    bot = WikiBot(channel, nickname, server, port)
    bot.start()
