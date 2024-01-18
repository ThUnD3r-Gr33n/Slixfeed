#!/bin/sh
#
# The following commands are used to
# prepare a package file for Slixfeed.
#
# Thank you to graingert and grym
# from #python on irc.libera.chat

pipx run setup-py-upgrade .
ini2toml setup.cfg > pyproject.toml
