# susm Dictionary

This is the quick reference for writing susm programs.

susm is stack based. Instructions read and write values from the top of the stack.

## Basics

Each instruction goes on its own line:

```susm
vent 40
vent 2
suspicious
yap
```

Lines can include comments after `#`:

```susm
vent 83 # ASCII S
yapc
```

Values are signed 64-bit integers.

## Stack Effects

Stack effects are written as:

```text
before -- after
```

The rightmost value is the top of the stack.

For example:

```text
a b -- c
```

means the instruction pops `b`, then pops `a`, then pushes `c`.

## Instructions

| Instruction | Stack effect | Meaning |
| --- | --- | --- |
| `vent <number>` | `-- number` | Push a signed 64-bit integer onto the stack. |
| `eject` | `value --` | Pop and discard the top value. |
| `suspicious` | `a b -- result` | Add `a + b` and push the result. |
| `impostor` | `a b -- result` | Subtract `a - b` and push the result. |
| `yap` | `value --` | Print the top value as a decimal integer, followed by a newline. |
| `yapc` | `value --` | Print the low byte of the top value as an ASCII character. |

## Examples

Print a number:

```susm
vent 40
vent 2
suspicious
yap
```

Output:

```text
42
```

Print characters from ASCII codes:

```susm
vent 83
yapc
vent 85
yapc
vent 83
yapc
vent 10
yapc
```

Output:

```text
SUS
```

Subtract:

```susm
vent 10
vent 3
impostor
yap
```

Output:

```text
7
```

Discard a value:

```susm
vent 123
eject
vent 9
yap
```

Output:

```text
9
```

## Common Errors

Stack underflow happens when an instruction needs a value that is not on the stack:

```susm
yap
```

Unknown instructions are rejected:

```susm
sus
```

Numbers must fit in signed 64 bits:

```text
-9223372036854775808 to 9223372036854775807
```
