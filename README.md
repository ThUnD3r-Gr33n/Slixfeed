# Syndication bot for the XMPP communication network

## Slixfeed

Slixfeed aims to be an easy to use and fully-featured news aggregator bot for XMPP. It provides a convenient access to Blogs, Fediverse and News websites along with filtering functionality.

Slixfeed is primarily designed for XMPP (aka Jabber).

Visit https://xmpp.org/software/ for more information.

## XMPP

XMPP is the Extensible Messaging and Presence Protocol, a set of open technologies for instant messaging, presence, multi-party chat, voice and video calls, collaboration, lightweight middleware, content syndication, and generalized routing of XML data.

Visit https://xmpp.org/about/ for more information on the XMPP protocol.

## Getting Started
```
$ python __main__.py
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
- [Schimon](xmpp:sch@pimux.de?message) (Author).
- [Laura](xmpp:lauranna@404.city?message) (Instructor, Mentor and Co-Author).

## Acknowledgment
Special thank you to Mrs. Lapina who instructed me all the way to complete this, in addition to significant code fixes.

Laura, I thank you greatly for your encouragement, time and help.

May this bot be a life changing factor to people the world over.

This bot would not be a reality without you.

## License
MIT license

## Copyright
- Schimon Zackary 2022 - 2023
- Laura Lapina 2022 - 2023

## Similar Projects
Please visit our friends who offer different approach to convey RSS to XMPP.

* [AtomToPubsub](https://github.com/imattau/atomtopubsub)
RSS feeds as XMPP Pubsub Nodes.

* [feed-to-muc](https://salsa.debian.org/mdosch/feed-to-muc)
An XMPP bot which posts to a MUC (groupchat) if there is an update in newsfeeds.

* [JabRSS](http://www.jotwewe.de/de/xmpp/jabrss/jabrss_en.htm)
Never miss a headline again! JabRSS is a simple RSS (RDF Site Summary) headline notification service for Jabber.

* [Morbot](https://codeberg.org/TheCoffeMaker/Morbot)
Morbo is a simple Slixmpp bot that will take new articles from listed RSS feeds and send them to assigned XMPP MUCs (groupchats).
