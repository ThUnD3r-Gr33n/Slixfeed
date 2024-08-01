# Set Slixfeed Ad-Hoc Commands in MUC

This documents provides instructions for setting Slixfeed Ad-Hoc Commands on your XMPP server

These instruction are currently applied only to Prosody XMPP server.

We encourage to contribute instructions for other XMPP servers.

## Prosody

First of all install the relative Community Module:

```
$ sudo prosodyctl install --server=https://modules.prosody.im/rocks/ mod_muc_adhoc_bots
```

Then enable the module in your **MUC component** (`/etc/prosody/prosody.cfg.lua`), like this:

```
modules_enabled = {
"muc_mam",
"vcard_muc",
…
"muc_adhoc_bots",
…
"server_contact_info"
}
```

Last part is the bot's configuration, which goes again under the MUC component settings:

```
adhoc_bots = { "bot@jabber.i2p/slixfeed" }
```

Substitute `bot@jabber.i2p/slixfeed` with your bot JID and device name which has to correspond to `accounts.toml` settings for Slixfeed configuration:

```
[xmpp.client]
alias = "Slixfeed"
jid = "bot@jabber.i2p/slixfeed"
```

Reload the Prosody config and then load the module you just enabled under MUC component, or simply restart the XMPP server.

```
$ sudo prosodyctl shell

prosody> config:reload()
prosody> module:load('muc_adhoc_bots', "muc_component.jabber.i2p")
prosody> bye
```

Authors:

- Simone Canaletti (roughnecks)