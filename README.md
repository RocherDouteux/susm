# susm

susm is a tiny meme stack language.

Read [DICTIONARY.md](DICTIONARY.md) for the language reference.

## Instructions

| susm | Meaning |
| --- | --- |
| `vent <number>` | push a number onto the stack |
| `eject` | pop and discard the top value |
| `suspicious` | pop two values, add them, push the result |
| `impostor` | pop two values, subtract right from left, push the result |
| `yap` | pop and print the top value |
| `yapc` | pop and print the low byte as an ASCII character |

Lines can include comments after `#`.

Values are signed 64-bit integers, matching the current x86-64 compiler target.

## Usage

```powershell
python susm.py run examples/first.susm
python susm.py run examples/chars.susm
python susm.py run examples/first.susm --show-stack
python susm.py compile examples/first.susm
python susm.py check
```

`compile` defaults to the native target for the host OS. You can also target Linux ELF or Windows PE explicitly:

```powershell
python susm.py compile examples/first.susm --target elf
python susm.py compile examples/first.susm --target pe
```

By default, `compile` creates an executable. You can also stop earlier in the pipeline:

```powershell
python susm.py compile examples/first.susm --target elf --emit asm
python susm.py compile examples/first.susm --target elf --emit obj
python susm.py compile examples/first.susm --target pe --emit asm
python susm.py compile examples/first.susm --target pe --emit obj
```

Toolchain requirements:

| Target | Tools |
| --- | --- |
| `elf` | NASM and Linux/WSL `ld`, or `ld.lld` |
| `pe` | NASM and `gcc` or `x86_64-w64-mingw32-gcc` |

Check the available toolchain:

```powershell
python susm.py check
python susm.py check --target all
python susm.py check --target elf --emit obj
```
