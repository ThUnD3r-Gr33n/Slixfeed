#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

TODO

1) Deprecate "add" (see above) and make it interactive.
   Slixfeed: Do you still want to add this URL to subscription list?
   See: case _ if command_lowercase.startswith("add"):

2) If subscription is inadequate (see XmppPresence.request), send a message that says so.

    elif not self.client_roster[jid]["to"]:
        breakpoint()
        message.reply("Share online status to activate bot.").send()
        return

3) Set timeout for moderator interaction.
   If moderator interaction has been made, and moderator approves the bot, then
   the bot will add the given groupchat to bookmarks; otherwise, the bot will
   send a message that it was not approved and therefore leaves the groupchat.

"""

from slixfeed.log import Logger
from slixmpp import JID
from slixmpp.exceptions import IqTimeout, IqError
from slixmpp.stanza import Message
from slixmpp_omemo import PluginCouldNotLoad, MissingOwnKey, EncryptionPrepareException
from slixmpp_omemo import UndecidedException, UntrustedException, NoAvailableSession
from omemo.exceptions import MissingBundleException


logger = Logger(__name__)


    # for task in main_task:
    #     task.cancel()

    # Deprecated in favour of event "presence_available"
    # if not main_task:
    #     await select_file()


class XmppOmemo:


    async def decrypt(self, message: Message, allow_untrusted: bool = False):
        jid = message['from']
        try:
            message_omemo_encrypted = message['omemo_encrypted']
            message_body = await self['xep_0384'].decrypt_message(
                message_omemo_encrypted, jid, allow_untrusted)
            # decrypt_message returns Optional[str]. It is possible to get
            # body-less OMEMO message (see KeyTransportMessages), currently
            # used for example to send heartbeats to other devices.
            if message_body is not None:
                response = message_body.decode('utf8')
                omemo_decrypted = True
            else:
                response = omemo_decrypted = None
        except (MissingOwnKey,) as exn:
            # The message is missing our own key, it was not encrypted for
            # us, and we can't decrypt it.
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (MissingOwnKey).')
            omemo_decrypted = False
            logger.error(exn)
        except (NoAvailableSession,) as exn:
            # We received a message from that contained a session that we
            # don't know about (deleted session storage, etc.). We can't
            # decrypt the message, and it's going to be lost.
            # Here, as we need to initiate a new encrypted session, it is
            # best if we send an encrypted message directly. XXX: Is it
            # where we talk about self-healing messages?
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (NoAvailableSession).')
            omemo_decrypted = False
            logger.error(exn)
        except (UndecidedException, UntrustedException) as exn:
            # We received a message from an untrusted device. We can
            # choose to decrypt the message nonetheless, with the
            # `allow_untrusted` flag on the `decrypt_message` call, which
            # we will do here. This is only possible for decryption,
            # encryption will require us to decide if we trust the device
            # or not. Clients _should_ indicate that the message was not
            # trusted, or in undecided state, if they decide to decrypt it
            # anyway.
            response = (f'Error: Device "{exn.device}" is not present in the '
                        'trusted devices of Slixfeed.')
            omemo_decrypted = False
            logger.error(exn)
            # We resend, setting the `allow_untrusted` parameter to True.
            await XmppChat.process_message(self, message, allow_untrusted=True)
        except (EncryptionPrepareException,) as exn:
            # Slixmpp tried its best, but there were errors it couldn't
            # resolve. At this point you should have seen other exceptions
            # and given a chance to resolve them already.
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (EncryptionPrepareException).')
            omemo_decrypted = False
            logger.error(exn)
        except (Exception,) as exn:
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (Unknown).')
            omemo_decrypted = False
            logger.error(exn)
            raise

        return response, omemo_decrypted


    async def encrypt(self, jid: JID, message_body):
        expect_problems = {}  # type: Optional[Dict[JID, List[int]]]
        while True:
            try:
                # `encrypt_message` excepts the plaintext to be sent, a list of
                # bare JIDs to encrypt to, and optionally a dict of problems to
                # expect per bare JID.
                #
                # Note that this function returns an `<encrypted/>` object,
                # and not a full Message stanza. This combined with the
                # `recipients` parameter that requires for a list of JIDs,
                # allows you to encrypt for 1:1 as well as groupchats (MUC).
                #
                # `expect_problems`: See EncryptionPrepareException handling.
                recipients = [jid]
                message_body = await self['xep_0384'].encrypt_message(
                    message_body, recipients, expect_problems)
                omemo_encrypted = True
                break
            except UndecidedException as exn:
                # The library prevents us from sending a message to an
                # untrusted/undecided barejid, so we need to make a decision here.
                # This is where you prompt your user to ask what to do. In
                # this bot we will automatically trust undecided recipients.
                await self['xep_0384'].trust(exn.bare_jid, exn.device, exn.ik)
                omemo_encrypted = False
            # TODO: catch NoEligibleDevicesException
            except EncryptionPrepareException as exn:
                # This exception is being raised when the library has tried
                # all it could and doesn't know what to do anymore. It
                # contains a list of exceptions that the user must resolve, or
                # explicitely ignore via `expect_problems`.
                # TODO: We might need to bail out here if errors are the same?
                for error in exn.errors:
                    if isinstance(error, MissingBundleException):
                        # We choose to ignore MissingBundleException. It seems
                        # to be somewhat accepted that it's better not to
                        # encrypt for a device if it has problems and encrypt
                        # for the rest, rather than error out. The "faulty"
                        # device won't be able to decrypt and should display a
                        # generic message. The receiving end-user at this
                        # point can bring up the issue if it happens.
                        message_body = (f'Could not find keys for device '
                                        '"{error.device}"'
                                        f' of recipient "{error.bare_jid}". '
                                        'Skipping.')
                        omemo_encrypted = False
                        jid = JID(error.bare_jid)
                        device_list = expect_problems.setdefault(jid, [])
                        device_list.append(error.device)
            except (IqError, IqTimeout) as exn:
                message_body = ('An error occured while fetching information '
                                'on a recipient.\n%r' % exn)
                omemo_encrypted = False
            except Exception as exn:
                message_body = ('An error occured while attempting to encrypt'
                                '.\n%r' % exn)
                omemo_encrypted = False
                raise

        return message_body, omemo_encrypted
