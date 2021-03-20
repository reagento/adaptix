import ast
import inspect
import textwrap
from copy import copy, deepcopy
from typing import Any

VAR_NAME = "______"
FOR_NAME_TMPL = "_{}__{}__{}"


class RewriteName(ast.NodeTransformer):
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.replaces = []
        self.for_number = -1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        node.decorator_list = []  # remove decorators because they will be applied later
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> Any:
        for mapping in self.replaces[::-1]:
            if node.id in mapping:
                node.id = mapping[node.id]
                break

        if node.id in self.kwargs:
            value = self.kwargs[node.id]
            if isinstance(value, (str, int)):
                return ast.Constant(
                    value=value,
                    lineno=node.lineno,
                    kind=None,
                    col_offset=node.col_offset
                )
        return node

    def visit_For(self, node: ast.For) -> Any:
        self.for_number += 1
        try:
            names = self.get_names(node.target)
            iterable = self.eval(node.iter)
            result = []
            for n, elem in enumerate(iterable):
                unpacked = dict(self.unpack(n, names, elem))
                self.replaces.append(dict(self.name_mapping(names, n)))
                self.kwargs.update(unpacked)
                result.extend(self.visit_copy(node.body))
                self.replaces.pop()
            return result
        except Exception as e:
            self.generic_visit(node)
            return node

    def visit_copy(self, body):
        result = []
        for body_item in deepcopy(body):
            body_item = self.visit(body_item)
            if isinstance(body_item, (list, tuple)):
                result.extend(body_item)
            elif body_item:
                result.append(body_item)
        return result
    def name_mapping(self, names, n):
        if isinstance(names, str):
            yield names, FOR_NAME_TMPL.format(names, self.for_number, n)
        else:
            for name in names:
                yield from self.name_mapping(name, n)

    def get_names(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, (ast.Tuple, ast.List)):
            return [self.get_names(n) for n in node.elts]
        else:
            raise TypeError(f"Cannot get names from {node}")

    def unpack(self, n, names, container):
        if isinstance(names, str):
            yield FOR_NAME_TMPL.format(names, self.for_number, n), container
        if isinstance(names, list):
            if len(names) != len(container):
                raise ValueError(f"Cannot unpack {len(container)} items to {len(names)} variables")
            for name, element in zip(names, container):
                yield from self.unpack(n, name, element)

    def eval(self, expr):
        m = ast.Module(
            body=[ast.Assign(
                targets=[
                    ast.Name(VAR_NAME, ctx=ast.Store(), lineno=1, col_offset=0)
                ],
                value=expr,
                lineno=1, col_offset=0
            )],
            type_ignores=[],
        )
        m = self.visit(m)
        m = ast.fix_missing_locations(m)
        code = compile(m, filename='dataclass_factory/stub.py', mode='exec')
        namespace = copy(self.kwargs)
        exec(code, namespace)
        return namespace[VAR_NAME]

    def visit_If(self, node):
        try:
            res = self.eval(node.test)
            if res:
                return self.visit_copy(node.body)
            else:
                return None
        except Exception as e:
            self.generic_visit(node)
            return node


def optimize(locals, globals):
    def dec(func):
        freevars = func.__code__.co_freevars
        known_vars = {}
        known_vars.update(globals)
        for k, v in locals.items():
            if k in freevars:
                known_vars[k] = v

        text = inspect.getsource(func)
        text = "\n" * (func.__code__.co_firstlineno - 1) + textwrap.dedent(text)
        tree = ast.parse(text)

        new_tree = RewriteName(known_vars).visit(tree)
        code = compile(new_tree, filename=inspect.getfile(func), mode='exec')
        namespace = copy(known_vars)
        exec(code, namespace)
        return namespace[func.__name__]

    return dec
