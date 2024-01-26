#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def identity(self, category):
    """
    Identify for Service Duscovery

    Parameters
    ----------
    category : str
        "client" or "service".

    Returns
    -------
    None.

    """
    self["xep_0030"].add_identity(
        category=category,
        itype="news",
        name="slixfeed",
        node=None,
        jid=self.boundjid.full,
    )