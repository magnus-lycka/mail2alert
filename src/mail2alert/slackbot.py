import logging

from mail2alert.common import AlertLevels
from mail2alert.config import Configuration

from aioslacker import Slacker, Error as SlackerError


class SlackMessage:
    def __init__(self, message):
        self.original = message

    @property
    def text(self):
        return "Message from %s" % self.original.get('From')

    @property
    def attachment(self):
        return dict(
            title=self.original['Subject'],
            text=self.original.body,
            color=self.color
        )

    @property
    def color(self):
        return {
            AlertLevels.PRIMARY: '#4ABCF9',
            AlertLevels.SECONDARY: '#E7E8EA',
            AlertLevels.SUCCESS: '#2FA44F',
            AlertLevels.DANGER: '#D50200',
            AlertLevels.WARNING: '#DE9E31',
            AlertLevels.INFO: '#D1ECF1',
            AlertLevels.LIGHT: '#FFFFFF',
            AlertLevels.DARK: '#666666',
        }[self.original.alert_level]

    async def post(self, channels):
        token = Configuration()['slack-token']

        async with Slacker(token) as slack:
            for channel in channels:
                try:
                    await slack.chat.post_message(
                        channel,
                        text=self.text,
                        attachments=[self.attachment]
                    )
                except SlackerError as error:
                    logging.error("SlackMessage.post: %s", error)
