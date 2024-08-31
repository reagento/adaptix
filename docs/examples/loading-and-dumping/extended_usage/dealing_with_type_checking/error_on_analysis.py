from typing import get_type_hints

from .chat import Chat
from .message import Message

try:
    get_type_hints(Chat)
except NameError as e:
    assert str(e) == "name 'Message' is not defined"


try:
    get_type_hints(Message)
except NameError as e:
    assert str(e) == "name 'Chat' is not defined"
