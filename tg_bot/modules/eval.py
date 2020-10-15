import io
import os
# Common imports for eval
import textwrap
import traceback
from contextlib import redirect_stdout

from tg_bot import LOGGER, dispatcher
from tg_bot.modules.helper_funcs.chat_status import dev_plus
from telegram import ParseMode, Update
from telegram.ext import CallbackContext, CommandHandler

namespaces = {}


def namespace_of(chat, update, bot):
    if chat not in namespaces:
        namespaces[chat] = {
            '__builtins__': globals()['__builtins__'],
            'bot': bot,
            'effective_message': update.effective_message,
            'effective_user': update.effective_user,
            'effective_chat': update.effective_chat,
            'update': update
        }

    return namespaces[chat]


def log_input(update):
    user = update.effective_user.id
    chat = update.effective_chat.id
    LOGGER.info(
        f"IN: {update.effective_message.text} (user={user}, chat={chat})")


def send(msg, bot, update):
    if len(str(msg)) > 2000:
        with io.BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            bot.send_document(
                chat_id=update.effective_chat.id, document=out_file)
    else:
        LOGGER.info(f"OUT: '{msg}'")
        bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"`{msg}`",
            parse_mode=ParseMode.MARKDOWN)


@dev_plus
def evaluate(update: Update, context: CallbackContext):
    bot = context.bot
    send(do(eval, bot, update), bot, update)



@dev_plus
def execute(update: Update, context: CallbackContext):
    bot = context.bot
    send(do(exec, bot, update), bot, update)


def cleanup_code(code):
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])
    return code.strip('` \n')


def do(func, bot, update):
    log_input(update)
    content = update.message.text.split(' ', 1)[-1]
    body = cleanup_code(content)
    env = namespace_of(update.message.chat_id, update, bot)

    os.chdir(os.getcwd())
    with open(
            os.path.join(os.getcwd(),
                         'SaitamaRobot/modules/helper_funcs/temp.txt'),
            'w') as temp:
        temp.write(body)

    stdout = io.StringIO()

    to_compile = f'def func():\n{textwrap.indent(body, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f'{e.__class__.__name__}: {e}'

    func = env['func']

    try:
        with redirect_stdout(stdout):
            func_return = func()
    except Exception as e:
        value = stdout.getvalue()
        return f'{value}{traceback.format_exc()}'
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f'{value}'
            else:
                try:
                    result = f'{repr(eval(body, env))}'
                except:
                    pass
        else:
            result = f'{value}{func_return}'
        if result:
            return result




@dev_plus
def clear(update: Update, context: CallbackContext):
    bot = context.bot
    log_input(update)
    global namespaces
    if update.message.chat_id in namespaces:
        del namespaces[update.message.chat_id]
    send("Cleared locals.", bot, update)


eval_handler = CommandHandler(("e", "ev", "eva", "eval"), evaluate, run_async=True)
exec_handler = CommandHandler(("x", "ex", "exe", "exec", "py"), execute, run_async=True)
clear_handler = CommandHandler("clearlocals", clear, run_async=True)

dispatcher.add_handler(eval_handler)
dispatcher.add_handler(exec_handler)
dispatcher.add_handler(clear_handler)

__mod_name__ = "Eval Module"
