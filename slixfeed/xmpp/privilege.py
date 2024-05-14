#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def is_access(self, jid_bare, jid_full, chat_type):
    """Determine access privilege"""
    operator = is_operator(self, jid_bare)
    if operator:
        if chat_type == 'groupchat':
            if is_moderator(self, jid_bare, jid_full):
                access = True
        else:
            access = True
    else:
        access = False
    return access


def is_operator(self, jid_bare):
    """Check if given JID is an operator"""
    result = False
    for operator in self.operators:
        if jid_bare == operator['jid']:
            result = True
            # operator_name = operator['name']
            break
    return result


def is_moderator(self, jid_bare, jid_full):
    """Check if given JID is a moderator"""
    alias = jid_full[jid_full.index('/')+1:]
    role = self.plugin['xep_0045'].get_jid_property(jid_bare, alias, 'role')
    if role == 'moderator':
        result = True
    else:
        result = False
    return result


def is_member(self, jid_bare, jid_full):
    """Check if given JID is a member"""
    alias = jid_full[jid_full.index('/')+1:]
    affiliation = self.plugin['xep_0045'].get_jid_property(jid_bare, alias, 'affiliation')
    if affiliation == 'member':
        result = True
    else:
        result = False
    return result