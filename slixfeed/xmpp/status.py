#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def process_task_message(self, jid, status_message):
    self.send_presence(
        pshow="dnd",
        pstatus=status_message,
        pto=jid,
        )
