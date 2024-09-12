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

import json
from omemo.storage import Just, Maybe, Nothing, Storage
from omemo.types import DeviceInformation, JSONType
from slixfeed.log import Logger
from slixmpp import JID
from slixmpp.exceptions import IqTimeout, IqError
#from slixmpp.plugins import register_plugin
from slixmpp.stanza import Message
from slixmpp_omemo import TrustLevel, XEP_0384
from typing import Any, Dict, FrozenSet, Literal, Optional, Union

logger = Logger(__name__)

    # for task in main_task:
    #     task.cancel()

    # Deprecated in favour of event "presence_available"
    # if not main_task:
    #     await select_file()


class XmppOmemo:


    async def decrypt(self, stanza: Message):

        omemo_decrypted = None

        mto = stanza["from"]
        mtype = stanza["type"]

        namespace = self['xep_0384'].is_encrypted(stanza)
        if namespace is None:
            omemo_decrypted = False
            response = f"Unencrypted message or unsupported message encryption: {stanza['body']}"
        else:
            print(f'Message in namespace {namespace} received: {stanza}')
            try:
                response, device_information = await self['xep_0384'].decrypt_message(stanza)
                print(f'Information about sender: {device_information}')
                omemo_decrypted = True
            except Exception as e:  # pylint: disable=broad-exception-caught
                response = f'Error {type(e).__name__}: {e}'

        return response, omemo_decrypted


    async def encrypt(
        self,
        mto: JID,
        mtype: Literal['chat', 'normal'],
        mbody: str
    ) -> None:
        
        if isinstance(mbody, str):
            reply = self.make_message(mto=mto, mtype=mtype)
            reply['body'] = mbody

        reply.set_to(mto)
        reply.set_from(self.boundjid)

        # It might be a good idea to strip everything except for the body from the stanza,
        # since some things might break when echoed.
        message, encryption_errors = await self['xep_0384'].encrypt_message(reply, mto)

        if len(encryption_errors) > 0:
            print(f'There were non-critical errors during encryption: {encryption_errors}')
            # log.info(f'There were non-critical errors during encryption: {encryption_errors}')

        # for namespace, message in messages.items():
        #     message['eme']['namespace'] = namespace
        #     message['eme']['name'] = self['xep_0380'].mechanisms[namespace]

        return message, True


    async def _decrypt(self, message: Message, allow_untrusted: bool = False):
        jid = message['from']
        try:
            print('XmppOmemo.decrypt')
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
                omemo_decrypted = response = None
            retry = None
        except (MissingOwnKey,) as exn:
            print('XmppOmemo.decrypt. except: MissingOwnKey')
            # The message is missing our own key, it was not encrypted for
            # us, and we can't decrypt it.
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (MissingOwnKey).')
            omemo_decrypted = False
            retry = False
            logger.error(exn)
        except (NoAvailableSession,) as exn:
            print('XmppOmemo.decrypt. except: NoAvailableSession')
            # We received a message from that contained a session that we
            # don't know about (deleted session storage, etc.). We can't
            # decrypt the message, and it's going to be lost.
            # Here, as we need to initiate a new encrypted session, it is
            # best if we send an encrypted message directly. XXX: Is it
            # where we talk about self-healing messages?
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (NoAvailableSession).')
            omemo_decrypted = False
            retry = False
            logger.error(exn)
        except (UndecidedException, UntrustedException) as exn:
            print('XmppOmemo.decrypt. except: UndecidedException')
            print('XmppOmemo.decrypt. except: UntrustedException')
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
            retry = True
            logger.error(exn)
            # We resend, setting the `allow_untrusted` parameter to True.
            # await XmppChat.process_message(self, message, allow_untrusted=True)
        except (EncryptionPrepareException,) as exn:
            print('XmppOmemo.decrypt. except: EncryptionPrepareException')
            # Slixmpp tried its best, but there were errors it couldn't
            # resolve. At this point you should have seen other exceptions
            # and given a chance to resolve them already.
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (EncryptionPrepareException).')
            omemo_decrypted = False
            retry = False
            logger.error(exn)
        except (Exception,) as exn:
            print('XmppOmemo.decrypt. except: Exception')
            response = ('Error: Your message has not been encrypted for '
                        'Slixfeed (Unknown).')
            omemo_decrypted = False
            retry = False
            logger.error(exn)
            raise

        return response, omemo_decrypted, retry


    async def _encrypt(self, jid: JID, message_body):
        print(jid)
        print(message_body)
        expect_problems = {}  # type: Optional[Dict[JID, List[int]]]
        while True:
            try:
                print('XmppOmemo.encrypt')
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
                print('XmppOmemo.encrypt. except: UndecidedException')
                # The library prevents us from sending a message to an
                # untrusted/undecided barejid, so we need to make a decision here.
                # This is where you prompt your user to ask what to do. In
                # this bot we will automatically trust undecided recipients.
                await self['xep_0384'].trust(exn.bare_jid, exn.device, exn.ik)
                omemo_encrypted = False
            # TODO: catch NoEligibleDevicesException
            except EncryptionPrepareException as exn:
                print('XmppOmemo.encrypt. except: EncryptionPrepareException')
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
                print('XmppOmemo.encrypt. except: IqError, IqTimeout')
                message_body = ('An error occured while fetching information '
                                'on a recipient.\n%r' % exn)
                omemo_encrypted = False
            except Exception as exn:
                print('XmppOmemo.encrypt. except: Exception')
                message_body = ('An error occured while attempting to encrypt'
                                '.\n%r' % exn)
                omemo_encrypted = False
                raise

        return message_body, omemo_encrypted


class StorageImpl(Storage):
    """
    Example storage implementation that stores all data in a single JSON file.
    """

    JSON_FILE = "/home/admin/omemo-echo-client.json"

    def __init__(self) -> None:
        super().__init__()

        self.__data: Dict[str, JSONType] = {}
        try:
            with open(self.JSON_FILE, encoding="utf8") as f:
                self.__data = json.load(f)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    async def _load(self, key: str) -> Maybe[JSONType]:
        if key in self.__data:
            return Just(self.__data[key])

        return Nothing()

    async def _store(self, key: str, value: JSONType) -> None:
        self.__data[key] = value
        with open(self.JSON_FILE, "w", encoding="utf8") as f:
            json.dump(self.__data, f)

    async def _delete(self, key: str) -> None:
        self.__data.pop(key, None)
        with open(self.JSON_FILE, "w", encoding="utf8") as f:
            json.dump(self.__data, f)


class XEP_0384Impl(XEP_0384):  # pylint: disable=invalid-name
    """
    Example implementation of the OMEMO plugin for Slixmpp.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pylint: disable=redefined-outer-name
        super().__init__(*args, **kwargs)

        # Just the type definition here
        self.__storage: Storage

    def plugin_init(self) -> None:
        self.__storage = StorageImpl()

        super().plugin_init()

    @property
    def storage(self) -> Storage:
        return self.__storage

    @property
    def _btbv_enabled(self) -> bool:
        return True

    async def _devices_blindly_trusted(
        self,
        blindly_trusted: FrozenSet[DeviceInformation],
        identifier: Optional[str]
    ) -> None:
        log.info(f"[{identifier}] Devices trusted blindly: {blindly_trusted}")

    async def _prompt_manual_trust(
        self,
        manually_trusted: FrozenSet[DeviceInformation],
        identifier: Optional[str]
    ) -> None:
        # Since BTBV is enabled and we don't do any manual trust adjustments in the example, this method
        # should never be called. All devices should be automatically trusted blindly by BTBV.

        # To show how a full implementation could look like, the following code will prompt for a trust
        # decision using `input`:
        session_mananger = await self.get_session_manager()

        for device in manually_trusted:
            while True:
                answer = input(f"[{identifier}] Trust the following device? (yes/no) {device}")
                if answer in { "yes", "no" }:
                    await session_mananger.set_trust(
                        device.bare_jid,
                        device.identity_key,
                        TrustLevel.TRUSTED.value if answer == "yes" else TrustLevel.DISTRUSTED.value
                    )
                    break
                print("Please answer yes or no.")

#register_plugin(XEP_0384Impl)
