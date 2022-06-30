# Slixfeed
Syndication bot for the XMPP communication network.

## Getting started
```
$ python slixfeed.py
Username: 
Password: 
```

## Usage
- Start bot;
- Add contact JID of Slixfeed to your roster;
- Open chat with Slixfeed;
- Add news source with `feed add URL`

```
feed add https://xmpp.org/feeds/all.atom.xml
feed add https://redecentralize.org/podcast/feed.rss
feed add http://hackerpublicradio.org/hpr_ogg_rss.php
```

## Roadmap
- Improve asynchronism hadling;
- Improve error handling;
- Add hash or urlencode;
- Add daemon interface;
- Add HTML support;
- Add feed history tables of last week and last month.

## Authors and acknowledgment
- Schimon Jehudah, Attorney at Law.
- [Alixander Court](https://alixandercourt.com/)
- [edhelas](https://github.com/edhelas/atomtopubsub)
- [imattau](https://github.com/imattau/atomtopubsub) (Some code, mostly URL handling, was taken from imattau)
- [Laura](xmpp:lauranna@404.city)
- [Link Mauve](https://linkmauve.fr/contact.xhtml)
- magicfelix (async)
- Slixmpp participants who chose to remain anonymous or not to appear in this list.

## License
AGPL-3.0 license

## Copyright
Schimon Jehudah 2022
