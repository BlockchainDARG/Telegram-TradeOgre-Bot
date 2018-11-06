import tradeogrebot.labels as lbl

from telegram.ext import RegexHandler, CommandHandler
from tradeogrebot.plugin import TradeOgreBotPlugin


class Back(TradeOgreBotPlugin):

    def get_handlers(self):
        return [self._get_back_handler(), self._get_cmd_handler()]

    def _get_back_handler(self):
        return RegexHandler(f"^({lbl.BTN_BACK})$", self.back)

    def _get_cmd_handler(self):
        return CommandHandler("back", self.back)
