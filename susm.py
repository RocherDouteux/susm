from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


I64_MIN = -(2**63)
I64_MAX = 2**63 - 1
U64_MOD = 2**64


@dataclass(frozen=True)
class Instruction:
    op: str
    arg: int | None
    line: int


@dataclass(frozen=True)
class ToolStatus:
    name: str
    ok: bool
    detail: str


OPS = {
    "vent": "push",
    "eject": "pop",
    "suspicious": "plus",
    "impostor": "minus",
    "yap": "print",
    "yapc": "print_char",
}


class SusmError(Exception):
    pass


def to_i64(value: int) -> int:
    value %= U64_MOD
    if value > I64_MAX:
        return value - U64_MOD
    return value


def parse(source: str) -> list[Instruction]:
    instructions: list[Instruction] = []

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        meme_op = parts[0]
        op = OPS.get(meme_op)
        if op is None:
            raise SusmError(f"line {line_number}: unknown instruction '{meme_op}'")

        if op == "push":
            if len(parts) != 2:
                raise SusmError(f"line {line_number}: vent expects exactly one number")
            try:
                arg = int(parts[1])
            except ValueError as exc:
                raise SusmError(f"line {line_number}: '{parts[1]}' is not a number") from exc
            if arg < I64_MIN or arg > I64_MAX:
                raise SusmError(f"line {line_number}: '{parts[1]}' does not fit in signed 64 bits")
        else:
            if len(parts) != 1:
                raise SusmError(f"line {line_number}: {meme_op} does not take an argument")
            arg = None

        instructions.append(Instruction(op=op, arg=arg, line=line_number))

    return instructions


def pop_stack(stack: list[int], line: int) -> int:
    if not stack:
        raise SusmError(f"line {line}: stack underflow")
    return stack.pop()


def execute(instructions: Iterable[Instruction]) -> list[int]:
    stack: list[int] = []

    for instruction in instructions:
        if instruction.op == "push":
            assert instruction.arg is not None
            stack.append(instruction.arg)
        elif instruction.op == "pop":
            pop_stack(stack, instruction.line)
        elif instruction.op == "plus":
            right = pop_stack(stack, instruction.line)
            left = pop_stack(stack, instruction.line)
            stack.append(to_i64(left + right))
        elif instruction.op == "minus":
            right = pop_stack(stack, instruction.line)
            left = pop_stack(stack, instruction.line)
            stack.append(to_i64(left - right))
        elif instruction.op == "print":
            print(pop_stack(stack, instruction.line))
        elif instruction.op == "print_char":
            print(chr(pop_stack(stack, instruction.line) & 0xFF), end="", flush=True)
        else:
            raise SusmError(f"line {instruction.line}: compiler bug for op '{instruction.op}'")

    return stack


def validate_stack(instructions: Iterable[Instruction]) -> None:
    depth = 0

    for instruction in instructions:
        if instruction.op == "push":
            depth += 1
        elif instruction.op in {"pop", "print", "print_char"}:
            if depth < 1:
                raise SusmError(f"line {instruction.line}: stack underflow")
            depth -= 1
        elif instruction.op in {"plus", "minus"}:
            if depth < 2:
                raise SusmError(f"line {instruction.line}: stack underflow")
            depth -= 1
        else:
            raise SusmError(f"line {instruction.line}: compiler bug for op '{instruction.op}'")


def emit_push(lines: list[str], register: str = "rax") -> None:
    lines.extend(
        [
            f"    mov [r15], {register}",
            "    add r15, 8",
        ]
    )


def emit_pop(lines: list[str], register: str) -> None:
    lines.extend(
        [
            "    sub r15, 8",
            f"    mov {register}, [r15]",
        ]
    )


def compile_to_x86_64_elf_asm(instructions: Iterable[Instruction]) -> str:
    instructions = list(instructions)
    validate_stack(instructions)

    lines = [
        "bits 64",
        "default rel",
        "",
        "section .text",
        "global _start",
        "",
        "_start:",
        "    lea r15, [susm_stack]",
    ]

    for instruction in instructions:
        lines.append(f"    ; susm line {instruction.line}")
        if instruction.op == "push":
            assert instruction.arg is not None
            lines.extend(
                [
                    f"    mov rax, {instruction.arg}",
                ]
            )
            emit_push(lines)
        elif instruction.op == "pop":
            emit_pop(lines, "rax")
        elif instruction.op == "plus":
            emit_pop(lines, "rbx")
            emit_pop(lines, "rax")
            lines.append("    add rax, rbx")
            emit_push(lines)
        elif instruction.op == "minus":
            emit_pop(lines, "rbx")
            emit_pop(lines, "rax")
            lines.append("    sub rax, rbx")
            emit_push(lines)
        elif instruction.op == "print":
            emit_pop(lines, "rdi")
            lines.append("    call print_i64")
        elif instruction.op == "print_char":
            emit_pop(lines, "rax")
            lines.extend(
                [
                    "    mov [char_buf], al",
                    "    mov rax, 1",
                    "    mov rdi, 1",
                    "    lea rsi, [char_buf]",
                    "    mov rdx, 1",
                    "    syscall",
                ]
            )
        else:
            raise SusmError(f"line {instruction.line}: compiler bug for op '{instruction.op}'")
        lines.append("")

    lines.extend(
        [
            "    mov rax, 60",
            "    xor rdi, rdi",
            "    syscall",
            "",
            "print_i64:",
            "    mov rax, rdi",
            "    lea rsi, [print_buf + 20]",
            "    mov byte [rsi], 10",
            "    mov rcx, 1",
            "    xor r8, r8",
            "    cmp rax, 0",
            "    jge .digits",
            "    neg rax",
            "    mov r8, 1",
            "",
            ".digits:",
            "    mov rbx, 10",
            "",
            ".digit_loop:",
            "    xor rdx, rdx",
            "    div rbx",
            "    add dl, '0'",
            "    dec rsi",
            "    mov [rsi], dl",
            "    inc rcx",
            "    test rax, rax",
            "    jnz .digit_loop",
            "",
            "    test r8, r8",
            "    jz .write",
            "    dec rsi",
            "    mov byte [rsi], '-'",
            "    inc rcx",
            "",
            ".write:",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    mov rdx, rcx",
            "    syscall",
            "    ret",
            "",
            "section .bss",
            "print_buf: resb 21",
            "char_buf: resb 1",
            "susm_stack: resq 1024",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def compile_to_x86_64_pe_asm(instructions: Iterable[Instruction]) -> str:
    instructions = list(instructions)
    validate_stack(instructions)

    lines = [
        "bits 64",
        "default rel",
        "",
        "extern printf",
        "global main",
        "",
        "section .text",
        "main:",
        "    sub rsp, 40",
        "    lea r15, [susm_stack]",
    ]

    for instruction in instructions:
        lines.append(f"    ; susm line {instruction.line}")
        if instruction.op == "push":
            assert instruction.arg is not None
            lines.append(f"    mov rax, {instruction.arg}")
            emit_push(lines)
        elif instruction.op == "pop":
            emit_pop(lines, "rax")
        elif instruction.op == "plus":
            emit_pop(lines, "rbx")
            emit_pop(lines, "rax")
            lines.append("    add rax, rbx")
            emit_push(lines)
        elif instruction.op == "minus":
            emit_pop(lines, "rbx")
            emit_pop(lines, "rax")
            lines.append("    sub rax, rbx")
            emit_push(lines)
        elif instruction.op == "print":
            emit_pop(lines, "rdx")
            lines.extend(
                [
                    "    lea rcx, [fmt_i64]",
                    "    call printf",
                ]
            )
        elif instruction.op == "print_char":
            emit_pop(lines, "rdx")
            lines.extend(
                [
                    "    and edx, 255",
                    "    lea rcx, [fmt_char]",
                    "    call printf",
                ]
            )
        else:
            raise SusmError(f"line {instruction.line}: compiler bug for op '{instruction.op}'")
        lines.append("")

    lines.extend(
        [
            "    xor eax, eax",
            "    add rsp, 40",
            "    ret",
            "",
            "section .data",
            "fmt_i64: db \"%lld\", 10, 0",
            "fmt_char: db \"%c\", 0",
            "",
            "section .bss",
            "susm_stack: resq 1024",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def load_program(path: Path) -> list[Instruction]:
    return parse(path.read_text(encoding="utf-8"))


def run_command(args: argparse.Namespace) -> int:
    instructions = load_program(args.file)
    stack = execute(instructions)
    if args.show_stack:
        print(f"stack: {stack}")
    return 0


def compile_command(args: argparse.Namespace) -> int:
    instructions = load_program(args.file)
    require_toolchain(args.target, args.emit)
    output = args.output or default_output_path(args.file, args.target, args.emit)
    asm_path = output if args.emit == "asm" else intermediate_path(output, f".{args.target}.asm")
    obj_path = output if args.emit == "obj" else intermediate_path(
        output, ".pe.obj" if args.target == "pe" else ".elf.o"
    )

    if args.target == "elf":
        asm = compile_to_x86_64_elf_asm(instructions)
    elif args.target == "pe":
        asm = compile_to_x86_64_pe_asm(instructions)
    else:
        raise SusmError(f"unsupported target '{args.target}'")

    asm_path.write_text(asm, encoding="utf-8")
    if args.emit == "asm":
        print(f"compiled {args.file} -> {asm_path}")
        return 0

    assemble(args.target, asm_path, obj_path)
    if args.emit == "obj":
        print(f"compiled {args.file} -> {obj_path}")
        return 0

    link(args.target, obj_path, output)
    print(f"compiled {args.file} -> {output}")
    return 0


def check_command(args: argparse.Namespace) -> int:
    targets = [args.target] if args.target != "all" else ["elf", "pe"]
    failed = False

    print(f"host: {platform_name()} ({native_target()} native target)")
    for target in targets:
        print(f"{target}:")
        for status in check_toolchain(target, args.emit):
            marker = "ok" if status.ok else "missing"
            print(f"  {marker}: {status.name} - {status.detail}")
            failed = failed or not status.ok

    return 1 if failed else 0


def default_output_path(source: Path, target: str, emit: str) -> Path:
    if emit == "asm":
        return source.with_suffix(".asm")
    if emit == "obj":
        return source.with_suffix(".obj" if target == "pe" else ".o")
    return source.with_suffix(".exe" if target == "pe" else "")


def intermediate_path(output: Path, suffix: str) -> Path:
    if output.suffix:
        return output.with_suffix(suffix)
    return output.with_name(output.name + suffix)


def run_tool(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SusmError(f"missing tool '{command[0]}'") from exc
    except subprocess.CalledProcessError as exc:
        raise SusmError(f"tool failed with exit code {exc.returncode}: {' '.join(command)}") from exc


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found is not None:
        return found

    scoop = os.environ.get("USERPROFILE")
    if scoop is None:
        return None

    shim_dir = Path(scoop) / "scoop" / "shims"
    app_bin_dir = Path(scoop) / "scoop" / "apps" / name / "current" / "bin"
    candidates = [
        shim_dir / name,
        shim_dir / f"{name}.exe",
        shim_dir / f"{name}.cmd",
        app_bin_dir / name,
        app_bin_dir / f"{name}.exe",
        app_bin_dir / f"{name}.cmd",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def require_tool(name: str) -> str:
    found = find_tool(name)
    if found is None:
        raise SusmError(f"missing tool '{name}'")
    return found


def check_toolchain(target: str, emit: str) -> list[ToolStatus]:
    if emit == "asm":
        return []

    statuses = [check_tool("nasm", f"required to assemble {target} objects")]
    if emit == "obj":
        return statuses

    if target == "elf":
        statuses.append(check_elf_linker())
    elif target == "pe":
        statuses.append(check_pe_linker())
    else:
        statuses.append(ToolStatus(target, False, "unsupported target"))

    return statuses


def require_toolchain(target: str, emit: str) -> None:
    missing = [status for status in check_toolchain(target, emit) if not status.ok]
    if missing:
        details = "; ".join(f"{status.name}: {status.detail}" for status in missing)
        raise SusmError(f"toolchain check failed for {target}/{emit}: {details}")


def check_tool(name: str, detail: str) -> ToolStatus:
    found = find_tool(name)
    if found is None:
        return ToolStatus(name, False, detail)
    return ToolStatus(name, True, found)


def check_elf_linker() -> ToolStatus:
    ld_lld = find_tool("ld.lld")
    if ld_lld is not None:
        return ToolStatus("ld.lld", True, ld_lld)

    ld = find_tool("ld")
    if ld is None:
        return ToolStatus("ld", False, "required to link ELF executables")
    if not linker_supports(ld, "elf_x86_64"):
        return ToolStatus("ld", False, f"{ld} does not support elf_x86_64; use Linux/WSL ld or install ld.lld")
    return ToolStatus("ld", True, ld)


def check_pe_linker() -> ToolStatus:
    gcc = find_tool("gcc")
    if gcc is not None:
        return ToolStatus("gcc", True, gcc)

    mingw_gcc = find_tool("x86_64-w64-mingw32-gcc")
    if mingw_gcc is not None:
        return ToolStatus("x86_64-w64-mingw32-gcc", True, mingw_gcc)

    return ToolStatus("gcc", False, "required to link PE executables; install gcc or x86_64-w64-mingw32-gcc")


def assemble(target: str, asm_path: Path, obj_path: Path) -> None:
    nasm = require_tool("nasm")
    fmt = "win64" if target == "pe" else "elf64"
    run_tool([nasm, f"-f{fmt}", str(asm_path), "-o", str(obj_path)])


def link(target: str, obj_path: Path, output: Path) -> None:
    if target == "elf":
        ld_lld = find_tool("ld.lld")
        if ld_lld is not None:
            run_tool([ld_lld, "-m", "elf_x86_64", str(obj_path), "-o", str(output)])
            return

        ld = require_tool("ld")
        if not linker_supports(ld, "elf_x86_64"):
            raise SusmError("available ld does not support elf_x86_64; use Linux/WSL ld or install ld.lld")
        run_tool([ld, "-m", "elf_x86_64", str(obj_path), "-o", str(output)])
        return

    linker = find_tool("gcc") or find_tool("x86_64-w64-mingw32-gcc")
    if linker is None:
        raise SusmError("missing PE linker: install gcc or x86_64-w64-mingw32-gcc")
    run_tool([linker, str(obj_path), "-o", str(output)])


def linker_supports(linker: str, emulation: str) -> bool:
    result = subprocess.run([linker, "-V"], capture_output=True, text=True, check=False)
    return emulation in result.stdout or emulation in result.stderr


def native_target() -> str:
    return "pe" if os.name == "nt" else "elf"


def platform_name() -> str:
    return "windows" if os.name == "nt" else "posix"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="susm", description="susm meme stack language")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="interpret a susm program")
    run_parser.add_argument("file", type=Path)
    run_parser.add_argument("--show-stack", action="store_true")
    run_parser.set_defaults(func=run_command)

    compile_parser = subparsers.add_parser("compile", help="compile a susm program")
    compile_parser.add_argument("file", type=Path)
    compile_parser.add_argument("-o", "--output", type=Path)
    compile_parser.add_argument("--target", choices=["elf", "pe"], default=native_target())
    compile_parser.add_argument("--emit", choices=["asm", "obj", "exe"], default="exe")
    compile_parser.set_defaults(func=compile_command)

    check_parser = subparsers.add_parser("check", help="check the susm toolchain")
    check_parser.add_argument("--target", choices=["native", "all", "elf", "pe"], default="native")
    check_parser.add_argument("--emit", choices=["asm", "obj", "exe"], default="exe")
    check_parser.set_defaults(func=lambda args: check_command(normalize_check_args(args)))

    return parser


def normalize_check_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.target == "native":
        args.target = native_target()
    return args


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except SusmError as exc:
        parser.exit(1, f"susm: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
