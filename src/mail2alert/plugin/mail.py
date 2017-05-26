import logging
from email import message_from_bytes
from email.policy import EmailPolicy

from mail2alert.actions import Actions
from mail2alert.rules import Rule


class Manager:
    """
    mail.Manager objects are handed mail messages.

    Based on the mail2alert configuration and mail content,
    they determine what to do with the mail message.
    """

    def __init__(self, conf):
        logging.info('Started %s', self.__class__)
        self.conf = conf

    @staticmethod
    def rules(rule_list):
        for rule in rule_list:
            yield MailRule(rule)

    @property
    def rule_funcs(self):
        return {'mail': Mail()}

    def wants_message(self, mail_from, rcpt_tos, content):
        """
        Determine whether the manager is interested in a certain message.
        """
        wanted = self.conf['messages-we-want']
        wanted_to = wanted.get('to')
        wanted_from = wanted.get('from')
        logging.debug('We vant to: %s or from: %s', wanted_to, wanted_from)
        logging.debug('We got to: %s and from: %s', rcpt_tos, mail_from)
        if wanted_to:
            return wanted_to in rcpt_tos
        if wanted_from:
            return wanted_from == mail_from

    async def process_message(self, mail_from, rcpt_tos, binary_content):
        logging.debug('process_message("%s", %s, %s)',
                      mail_from, rcpt_tos, binary_content)
        recipients = []
        msg = Message(binary_content)
        logging.info('Extracted message %s', msg)
        for rule in self.rules(self.conf['rules']):
            logging.debug('Check %s', rule)
            actions = Actions(rule.check(msg, self.rule_funcs))
            recipients.extend(actions.mailto)
        return mail_from, recipients, binary_content

    async def test(self):
        pass


class Mail:
    @staticmethod
    def in_subject(*words):
        def words_in_subject(msg):
            return all(
                word.lower() in msg['subject'].lower()
                for word in words
            )

        return words_in_subject


class Message(dict):
    def __init__(self, content):
        super().__init__()
        msg = message_from_bytes(
            content,
            policy=EmailPolicy(utf8=True, linesep='\r\n')
        )
        self['subject'] = msg['Subject']
        logging.info('Message with subject: %s', self['subject'])


class MailRule(Rule):
    pass

