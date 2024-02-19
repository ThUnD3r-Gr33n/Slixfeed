#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) remove_subscription (clean_roster)
   Remove presence from contacts that don't share presence.

"""

class XmppRoster:


    async def add(self, jid):
        """
        Add JID to roster.

        Add JID to roster if it is not already in roster.

        Parameters
        ----------
        jid : str
            Jabber ID.

        Returns
        -------
        None.
        """
        await self.get_roster()
        if jid not in self.client_roster.keys():
            self.update_roster(jid, subscription='both')


    async def get_contacts(self):
        await self.get_roster()
        contacts = self.client_roster
        return contacts


    def remove(self, jid):
        """
        Remove JID from roster.

        Parameters
        ----------
        jid : str
            Jabber ID.

        Returns
        -------
        None.
        """
        self.update_roster(jid, subscription='remove')


    def set_contact_name(self, jid, name):
        self.client_roster[jid]['name'] = name


    def get_contact_name(self, jid):
        name = self.client_roster[jid]['name']
        return name
