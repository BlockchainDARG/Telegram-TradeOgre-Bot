import tradeogrebot.emoji as emo
import tradeogrebot.labels as lbl

from enum import auto
from tradeogrebot.api.tradeogre import TradeOgre
from tradeogrebot.plugin import TradeOgreBotPlugin
from telegram import ParseMode, ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import MessageHandler, ConversationHandler, \
    RegexHandler, CallbackQueryHandler
from telegram.ext.filters import Filters
from tradeogrebot.config import ConfigManager as Cfg


class Trade(TradeOgreBotPlugin):

    FEE_ADD = 0.0001  # Percent

    # Conversation handler states
    TRADE_CHOOSE = auto()
    TRADE_BUY = auto()
    TRADE_SELL = auto()
    TRADE_PRICE = auto()
    TRADE_AMOUNT = auto()
    TRADE_CONFIRM = auto()

    def get_handlers(self):
        return [self._get_trade_handler(),
                self._get_trade_callback_handler()]

    def _get_trade_handler(self):
        return ConversationHandler(
            entry_points=[RegexHandler(f"^({lbl.TRADE})$", self._trade, pass_user_data=True)],
            states={
                self.TRADE_CHOOSE:
                    [RegexHandler(f"^({lbl.BUY})$", self._trade_buy, pass_user_data=True),
                     RegexHandler(f"^({lbl.SELL})$", self._trade_sell, pass_user_data=True),
                     RegexHandler(f"^({lbl.BACK})$", self.back)],
                self.TRADE_PRICE:
                    [RegexHandler(f"^({lbl.BACK})$", self.back),
                     MessageHandler(Filters.text, self._trade_price, pass_user_data=True)],
                self.TRADE_AMOUNT:
                    [RegexHandler(f"^({lbl.BACK})$", self.back),
                     MessageHandler(Filters.text, self._trade_amount, pass_user_data=True)]
            },
            fallbacks=[MessageHandler(Filters.text, self.back)],
            allow_reentry=True)

    def _get_trade_callback_handler(self):
        return CallbackQueryHandler(
            self._callback_trade,
            pattern="^(trade-yes|trade-no)$",
            pass_user_data=True)

    @TradeOgreBotPlugin.check_pair
    @TradeOgreBotPlugin.check_keys
    @TradeOgreBotPlugin.send_typing_action
    def _callback_trade(self, bot, update, user_data, data):
        query = update.callback_query

        if query.data == "trade-no":
            bot.edit_message_text(
                text=f"`{query.message.text}`\n"
                     f"{emo.CANCEL} *Order canceled*",
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                parse_mode=ParseMode.MARKDOWN)

            return

        pair = f"{user_data['pair'][0]}-{user_data['pair'][1]}"

        if user_data["type"] == "buy":
            trade = TradeOgre().buy(
                pair,
                user_data["qty"],
                user_data["price"],
                data.api_key,
                data.api_secret)
        elif user_data["type"] == "sell":
            trade = TradeOgre().sell(
                pair,
                user_data["amount"],
                user_data["price"],
                data.api_key,
                data.api_secret)

        if self.trade_ogre_api_error(trade, update):
            return ConversationHandler.END

        bot.edit_message_text(
            text=f"`{query.message.text}`\n"
                 f"{emo.FINISH} *Order created*",
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            parse_mode=ParseMode.MARKDOWN)

    @TradeOgreBotPlugin.add_user
    @TradeOgreBotPlugin.check_pair
    @TradeOgreBotPlugin.check_keys
    @TradeOgreBotPlugin.send_typing_action
    def _trade(self, bot, update, user_data, data):
        user_data.clear()
        user_data["pair"] = data.pair.split("-")
        user_data["key"] = data.api_key
        user_data["secret"] = data.api_secret

        update.message.reply_text(
            text=f"Do you want to *buy* or *sell* {user_data['pair'][1]}?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self._keyboard_trade())

        return self.TRADE_CHOOSE

    @TradeOgreBotPlugin.send_typing_action
    def _trade_buy(self, bot, update, user_data):
        user_data["type"] = "buy"
        coins = user_data['pair']

        ticker = TradeOgre().ticker(f"{coins[0]}-{coins[1]}")

        if self.trade_ogre_api_error(ticker, update):
            return ConversationHandler.END

        update.message.reply_text(
            text=f"Buy {coins[1]} for {coins[0]} to which price?\n"
                 f"`(Ticker: {ticker['price']} {coins[0]})`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboard_back())

        return self.TRADE_PRICE

    @TradeOgreBotPlugin.send_typing_action
    def _trade_sell(self, bot, update, user_data):
        user_data["type"] = "sell"
        coins = user_data["pair"]

        ticker = TradeOgre().ticker(f"{coins[0]}-{coins[1]}")

        if self.trade_ogre_api_error(ticker, update):
            return ConversationHandler.END

        update.message.reply_text(
            text=f"Sell {coins[1]} for {coins[0]} to which price?\n"
                 f"`(Ticker: {ticker['price']} {coins[0]})`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.keyboard_back())

        return self.TRADE_PRICE

    @TradeOgreBotPlugin.send_typing_action
    def _trade_price(self, bot, update, user_data):
        user_data["price"] = update.message.text
        coins = user_data["pair"]

        if user_data["type"] == "buy":
            balance = TradeOgre().balance(
                coins[0],
                key=user_data["key"],
                secret=user_data["secret"])

            if self.trade_ogre_api_error(balance, update):
                return ConversationHandler.END

            user_data["balance"] = balance

            message = f"Enter amount of {coins[0]} to spend\n" \
                      f"`(Available: {balance['available']} {coins[0]})`"

        elif user_data["type"] == "sell":
            balance = TradeOgre().balance(
                coins[1],
                key=user_data["key"],
                secret=user_data["secret"])

            if self.trade_ogre_api_error(balance, update):
                return ConversationHandler.END

            user_data["balance"] = balance

            message = f"Enter amount of {coins[1]} to sell\n" \
                      f"`(Available: {balance['available']} {coins[1]})`"

        update.message.reply_text(
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self._keyboard_amount())

        return self.TRADE_AMOUNT

    @TradeOgreBotPlugin.send_typing_action
    def _trade_amount(self, bot, update, user_data):
        balance = float(user_data["balance"]["available"])
        balance = balance - (balance / 100 * (Cfg.get("trading_fee") + self.FEE_ADD))

        if balance == 0:
            update.message.reply_text(
                text=f"{emo.ERROR} Your balance is 0",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.keyboard_main())

            return ConversationHandler.END

        if user_data["type"] == "buy":
            if update.message.text.endswith("%"):
                percent = int(update.message.text[:-1])
                user_data["amount"] = self.trm_zro((percent * balance) / 100.0)
            else:
                user_data["amount"] = update.message.text

            user_data["price"] = '{0:.8f}'.format(float(user_data["price"]))
            user_data["qty"] = float(user_data["amount"]) / float(user_data["price"])
            user_data["qty"] = self.trm_zro(user_data["qty"])

            update.message.reply_text(
                text=f"`"
                     f"{user_data['type']} "
                     f"{user_data['qty']} "
                     f"{user_data['pair'][1]}\n@ "
                     f"{user_data['price']} "
                     f"{user_data['pair'][0]}?\n"
                     f"(Value: {user_data['amount']} {user_data['pair'][0]})"
                     f"`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._keyboard_trade_confirm())

        elif user_data["type"] == "sell":
            if update.message.text.endswith("%"):
                percent = int(update.message.text[:-1])
                user_data["amount"] = self.trm_zro((percent * balance) / 100.0)
            else:
                user_data["amount"] = update.message.text

            user_data["price"] = '{0:.8f}'.format(float(user_data["price"]))
            value = float(user_data["amount"]) * float(user_data["price"])
            value = self.trm_zro(value)

            update.message.reply_text(
                text=f"`"
                     f"{user_data['type']} "
                     f"{user_data['amount']} "
                     f"{user_data['pair'][1]}\n@ "
                     f"{user_data['price']} "
                     f"{user_data['pair'][0]}?\n"
                     f"(Value: {value} {user_data['pair'][0]})"
                     f"`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self._keyboard_trade_confirm())

    def _keyboard_trade_confirm(self):
        keyboard_markup = [[
            InlineKeyboardButton("Yes", callback_data="trade-yes"),
            InlineKeyboardButton("No", callback_data="trade-no")]]

        return InlineKeyboardMarkup(keyboard_markup)

    def _keyboard_trade(self):
        buttons = [
            KeyboardButton(lbl.BUY),
            KeyboardButton(lbl.SELL)
        ]

        return ReplyKeyboardMarkup(
            self.build_menu(buttons, n_cols=2, footer_buttons=[KeyboardButton(lbl.BACK)]),
            resize_keyboard=True)

    def _keyboard_amount(self):
        buttons = [
            KeyboardButton(lbl.P25),
            KeyboardButton(lbl.P50),
            KeyboardButton(lbl.P75),
            KeyboardButton(lbl.P100),
        ]

        return ReplyKeyboardMarkup(
            self.build_menu(buttons, n_cols=4, footer_buttons=[KeyboardButton(lbl.BACK)]),
            resize_keyboard=True)
