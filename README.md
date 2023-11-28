# Slixfeed
Syndication bot for the XMPP communication network.

Slixfeed aims to be an easy to use and fully-featured news aggregator bot for XMPP. It provides a convenient access to Blogs, Fediverse and News websites along with filtering functionality.

Slixfeed is primarily designed for XMPP (aka Jabber).

Visit https://xmpp.org/software/ for more information.

XMPP is the Extensible Messaging and Presence Protocol, a set of open technologies for instant messaging, presence, multi-party chat, voice and video calls, collaboration, lightweight middleware, content syndication, and generalized routing of XML data.

Visit https://xmpp.org/about/ for more information on the XMPP protocol.

## Getting Started
```
$ python slixfeed.py
Username: 
Password: 
```

## Usage
- Start bot;
- Add contact JID of Slixfeed to your roster;
- Open chat with Slixfeed;
- Add news source by sending a `<url>` (in groupchat, use `!<url>`).

### Feeds
Example feeds you can subscribe to.
```
https://xmpp.org/feeds/all.atom.xml
https://takebackourtech.org/rss/
https://redecentralize.org/podcast/feed.rss
http://hackerpublicradio.org/hpr_ogg_rss.php
https://www.blacklistednews.com/rss.php
https://theconsciousresistance.com/feed/
```

## Roadmap
- Improve asynchronism hadling;
- Improve logging and error handling;
- Add daemon interface;
- Add HTML support (XHTML-IM);
- Add feed history tables of last week and last month.

## Authors
- Schimon Jehudah, Attorney at Law.
- [Laura](xmpp:lauranna@404.city) (Instructor, mentor and co-author).

## Acknowledgment
- [Alixander Court](https://alixandercourt.com/)
- [edhelas](https://github.com/edhelas/atomtopubsub)
- habnabit_ from #python on irc.libera.chat (SQL security)
- [imattau](https://github.com/imattau/atomtopubsub) (Some code, mostly URL handling, was taken from imattau)
- [Link Mauve](https://linkmauve.fr/contact.xhtml)
- magicfelix (async)
- Slixmpp participants who chose to remain anonymous or not to appear in this list.

## License
GPL-3.0 license

## Copyright
- Schimon Jehudah 2022 - 2023
- Laura 2022 - 2023

## Similar Projects
Please visit our friends who offer different approach to convey RSS to XMPP.

* [AtomToPubsub](https://github.com/imattau/atomtopubsub)
RSS feeds as XMPP Pubsub Nodes.

* [feed-to-muc](https://salsa.debian.org/mdosch/feed-to-muc)
An XMPP bot which posts to a MUC (groupchat) if there is an update in newsfeeds.

* [Morbot](https://codeberg.org/TheCoffeMaker/Morbot)
Morbo is a simple Slixmpp bot that will take new articles from listed RSS feeds and send them to assigned XMPP MUCs (groupchats).
