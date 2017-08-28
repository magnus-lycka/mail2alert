import logging

from mail2alert.common import AlertLevels
from mail2alert.config import Configuration

from aioslacker import Slacker, Error as SlackerError


class SlackMessage:
    def __init__(self, message):
        self.original = message

    @property
    def text(self):
        return "Message from: %s" % self.original.get('From')

    @property
    def full_attachment(self):
        return dict(
            title=self.original['Subject'],
            text=self.original.body,
            color=self.color
        )

    @property
    def brief_attachment(self):
        return dict(
            title=self.original['Subject'],
            text=self.original.body.split('\n')[0],
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

    async def post(self, channel_styles):
        token = Configuration()['slack-token']

        async with Slacker(token) as slack:
            for channel_style in channel_styles:
                channel = channel_style[0]
                if len(channel_style) > 1:
                    style = channel_style[1]
                else:
                    style = 'brief'
                try:
                    if style == 'brief':
                        await self.post_brief(slack, channel)
                    elif style == 'full':
                        await self.post_full(slack, channel)
                    else:
                        raise ValueError("Don't know slack message style: %s" % style)
                except SlackerError as error:
                    logging.error("SlackMessage.post: error=%s", error)
                    logging.error("SlackMessage.post: channel=%s", channel)

    async def post_full(self, slack, channel):
        logging.info("SlackMessage.post full to %s", channel)
        await slack.chat.post_message(
            channel,
            text=self.text,
            attachments=[self.full_attachment]
        )

    async def post_brief(self, slack, channel):
        logging.info("SlackMessage.post brief to %s", channel)
        await slack.chat.post_message(
            channel,
            text='',
            attachments=[self.brief_attachment]
        )
