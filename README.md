# Syndication bot for the XMPP communication network

## Slixfeed

Slixfeed aims to be an easy to use and fully-featured news aggregator bot for XMPP. It provides a convenient access to Blogs, Fediverse (i.e. Akkoma, Mastodon, Misskey, Pleroma etc.) and News websites.

## XMPP

XMPP is the Extensible Messaging and Presence Protocol, a set of open technologies for instant messaging, presence, multi-party chat, voice and video calls, collaboration, lightweight middleware, content syndication, and generalized routing of XML data.

Visit https://xmpp.org/about/ for more information on the XMPP protocol and https://xmpp.org/software/ for list of XMPP clients.

Slixfeed is primarily designed for XMPP (aka Jabber), yet it is built to be extended to other protocols.

### Features

#### Ease

Slixfeed automatically scans (i.e. crawls) for web feeds of given URL.

#### Export

Download articles as ePUB, HTML, Markdown and PDF.

#### Filtering

Filter using lists of allow and deny.

#### Multimedia

Display audios pictures and videos inline.

#### Privacy

Redirect to alternative back-ends, such as Invidious, Librarian, Nitter, for increased privacy, productivity and security.

#### Portable

Export and import feeds with a standard OPML file.

#### Simultaneous

Slixfeed is designed to handle multiple contacts, including groupchats, Simultaneously.

## Getting Started

### Install

Choose one of the following installation methods.

#### Using pip inside venv

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install git+https://gitgud.io/sjehuda/slixfeed
```

#### Using pipx

```
$ pipx install git+https://gitgud.io/sjehuda/slixfeed
```

### Upgrade

Upgrade using the following command.

```
$ pip install --upgrade slixfeed
```

### Start

```
$ slixfeed
```

### Usage

- Add the bot to contact list and follow it instructions.
- Send command `help` or `commands` for a list of commands.

## Roadmap

- Add service interface;
- Improve asynchronism hadling;
- Improve logging and error handling;
- Add daemon interface;
- Add HTML support (XHTML-IM);
- Add feed history tables of last week and last month.

## Authors

- [Laura](xmpp:lauranna@404.city?message) (Co-Author, Instructor and Mentor).
- [Schimon](xmpp:sch@pimux.de?message) (Author).

## Acknowledgment

Special thank you to Mrs. Lapina who instructed me all the way to complete this, in addition to significant code fixes.

Laura, I thank you greatly for your encouragement, time and help. This bot would not have existed without you.

May this bot be a life changing factor to people the world over.

## License

MIT license.

## Copyright

- Laura Lapina 2022 - 2023
- Schimon Zackary 2022 - 2024

## Similar Projects

Please visit our friends who offer different approach to convey RSS to XMPP.

* [AtomToPubsub](https://github.com/imattau/atomtopubsub)
RSS feeds as XMPP Pubsub Nodes.

* [err-rssreader](https://github.com/errbotters/err-rssreader)
A port of old Brutal's RSS Reader for Errbot.

* [feed-to-muc](https://salsa.debian.org/mdosch/feed-to-muc)
An XMPP bot which posts to a MUC (groupchat) if there is an update in newsfeeds.

* [JabRSS](http://www.jotwewe.de/de/xmpp/jabrss/jabrss_en.htm)
Never miss a headline again! JabRSS is a simple RSS (RDF Site Summary) headline notification service for Jabber.

* [Morbot](https://codeberg.org/TheCoffeMaker/Morbot)
Morbo is a simple Slixmpp bot that will take new articles from listed RSS feeds and send them to assigned XMPP MUCs (groupchats).
