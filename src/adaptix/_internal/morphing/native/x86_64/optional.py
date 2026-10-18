from dataclasses import dataclass

from adaptix._internal.morphing.native import descriptions
from adaptix._internal.morphing.native.runtime import optional_error


@dataclass(frozen=True)
class OptionalProgram(descriptions.OptionalProgram):
    def emit(self, c):
        missing, done = c.label("optional_none"), c.label("optional_ready")
        result = c.slot(owned=True)
        c.branch_if(c.data, None, missing)
        value = (
            c.inline_call(self.converter, c.data, optional_error, c.constant(self.tp), c.data)
            if self.tp is not None else c.inline_call(self.converter, c.data)
        )
        c.transfer(value, result)
        c.asm.jump(done)
        c.asm.label(missing)
        value = c.new_reference(None)
        c.transfer(value, result)
        c.asm.label(done)
        return result
