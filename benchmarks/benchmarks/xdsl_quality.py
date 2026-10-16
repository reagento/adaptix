import argparse
import json
from pathlib import Path

import capstone
from capstone.x86 import X86_OP_MEM, X86_REG_RBP, X86_REG_RSP
from llvmlite import binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    disassembler = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    disassembler.detail = True
    report = {}
    for path in sorted(args.artifacts.iterdir()):
        if path.suffix == ".o":
            with binding.ObjectFileRef.from_data(path.read_bytes()) as obj:
                text = b"".join(section.data() for section in obj.sections() if section.is_text())
        elif path.suffix == ".bin":
            text = path.read_bytes()
        else:
            continue
        instructions = list(disassembler.disasm(text, 0))
        report[path.stem] = {
            "text_bytes": len(text),
            "decoded_bytes": sum(instruction.size for instruction in instructions),
            "instructions": len(instructions),
            "stack_operands": sum(
                operand.type == X86_OP_MEM and operand.mem.base in (X86_REG_RBP, X86_REG_RSP)
                for instruction in instructions for operand in instruction.operands
            ),
            "calls": sum(instruction.mnemonic == "call" for instruction in instructions),
            "simd_register_instructions": sum(
                any(register in instruction.op_str for register in ("xmm", "ymm", "zmm"))
                for instruction in instructions
            ),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
