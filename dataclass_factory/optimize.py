import ast
import inspect
import textwrap
from copy import deepcopy


def clean_text(text):
    return textwrap.dedent(text)
    indent_len = len(text[:text.find('def')])
    strings = text.split('\n')
    new_strings = []
    for string in strings:
        new_string = string[indent_len:]
        new_strings.append(new_string)
    return '\n'.join(new_strings)


class RewriteName(ast.NodeTransformer):
    def __init__(self, kwargs):
        self.kwargs = kwargs

    def visit_If(self, node):
        try:
            m = ast.Module(
                body=[ast.Assign(
                    targets=[
                        ast.Name("________", ctx=ast.Store(), lineno=1, col_offset=0)
                    ],
                    value=node.test,
                    lineno=1, col_offset=0
                )],
                type_ignores=[],
            )
            code = compile(m, filename='blah', mode='exec')
            namespace = deepcopy(self.kwargs)
            exec(code, namespace)
            res = namespace["________"]
            if not res:
                return None
            else:
                return node.body
        except Exception as e:
            print("oops", e)
            return node


def cut_if(**kwargs):
    def dec(func):
        known_vars = {k: v for k, v in kwargs.items() if v != func}
        text = inspect.getsource(func)
        text = clean_text(text)
        tree = ast.parse(text)

        new_tree = ast.fix_missing_locations(RewriteName(known_vars).visit(tree))
        code = compile(new_tree, filename='blah', mode='exec')
        namespace = deepcopy(kwargs)
        exec(code, namespace)
        return namespace[func.__name__]

    return dec
