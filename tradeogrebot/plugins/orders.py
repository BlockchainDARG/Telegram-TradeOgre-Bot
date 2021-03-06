import tradeogrebot.emoji as emo
import tradeogrebot.labels as lbl

from tradeogrebot.api.tradeogre import TradeOgre
from tradeogrebot.plugin import TradeOgreBotPlugin
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import RegexHandler, CallbackQueryHandler, CommandHandler


class Orders(TradeOgreBotPlugin):

    def get_handlers(self):
        return [self._get_orders_handler(),
                self._get_orders_callback_handler(),
                self._get_cmd_handler()]

    def _get_cmd_handler(self):
        return CommandHandler("orders", self._orders)

    def _get_orders_handler(self):
        return RegexHandler(f"^({lbl.ORDERS})$", self._orders)

    def _get_orders_callback_handler(self):
        regex = "^[a-z0-9]{8}[-][a-z0-9]{4}[-][a-z0-9]{4}[-][a-z0-9]{4}[-][a-z0-9]{12}$"
        return CallbackQueryHandler(self._callback_orders, pattern=regex)

    @TradeOgreBotPlugin.add_user
    @TradeOgreBotPlugin.check_pair
    @TradeOgreBotPlugin.check_keys
    @TradeOgreBotPlugin.send_typing_action
    def _orders(self, bot, update, data):
        orders = TradeOgre().orders(key=data.api_key, secret=data.api_secret)

        if orders:
            coins = data.pair.split("-")

            for o in orders:
                market = o["market"].split("-")
                msg = f"`{o['type']} {o['quantity']} {market[1]}\n@ {o['price']} {market[0]}`"

                # Check if order is for active market
                if o["market"].split("-")[1] == coins[1]:
                    msg = "Active coin\n" + msg

                update.message.reply_text(
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self._keyboard_order_close(o["uuid"]))
        else:
            update.message.reply_text(
                text="No open orders",
                reply_markup=self.keyboard_main())

    @TradeOgreBotPlugin.send_typing_action
    def _callback_orders(self, bot, update):
        query = update.callback_query
        data = self.db.get_user_data(query.message.chat_id)

        close_order = TradeOgre().cancel(
            query.data,
            key=data.api_key,
            secret=data.api_secret)

        if not self.trade_ogre_api_error(close_order, update):
            bot.edit_message_text(
                text=f"`{query.message.text}`\n"
                     f"{emo.CANCEL} *Order closed*",
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                parse_mode=ParseMode.MARKDOWN)

    def _keyboard_order_close(self, uuid):
        keyboard_markup = [[InlineKeyboardButton("Close order", callback_data=uuid)]]
        return InlineKeyboardMarkup(keyboard_markup)
