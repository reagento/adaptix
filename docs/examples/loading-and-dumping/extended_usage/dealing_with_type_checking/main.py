# ruff: noqa: UP035, UP006
from typing import List, get_type_hints

from adaptix.type_tools import exec_type_checking

from . import chat, message

# You pass the module object
exec_type_checking(chat)
exec_type_checking(message)

# After these types can be extracted
assert get_type_hints(chat.Chat) == {
    "id": int,
    "name": str,
    "messages": List[message.Message],
}
assert get_type_hints(chat.Message) == {
    "id": int,
    "text": str,
    "chat": chat.Chat,
}
