# susm Dictionary

This page is the language reference for writing susm programs.

susm is stack based: values are pushed onto a stack, and most instructions use the values on top of that stack.

## First Program

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

What happened:

1. `vent 40` pushes `40`.
2. `vent 2` pushes `2`.
3. `suspicious` pops both values and pushes `42`.
4. `yap` prints `42`.

## File Rules

- One instruction per line.
- Empty lines are ignored.
- Anything after `#` is a comment.
- Numbers are signed 64-bit integers.

```susm
vent 83 # ASCII S
yapc
```

Valid number range:

```text
-9223372036854775808 to 9223372036854775807
```

## Reading Stack Effects

Stack effects show what an instruction consumes and produces:

```text
before -- after
```

The rightmost value is the top of the stack.

Example:

```text
a b -- result
```

This means:

1. `b` is on top of the stack.
2. The instruction pops `b`.
3. Then it pops `a`.
4. Then it pushes `result`.

## Quick Reference

| Instruction | Stack effect | Meaning |
| --- | --- | --- |
| `vent <number>` | `-- number` | Push a number. |
| `eject` | `value --` | Drop the top value. |
| `suspicious` | `a b -- result` | Add `a + b`. |
| `impostor` | `a b -- result` | Subtract `a - b`. |
| `yap` | `value --` | Print a number with a newline. |
| `yapc` | `value --` | Print the low byte as an ASCII character. |
| `label <name>` | `--` | Define a jump target. |
| `sus <name>` | `--` | Jump to a label. |
| `sussy <name>` | `value --` | Jump to a label if `value` is not zero. |
| `dupe` | `value -- value value` | Duplicate the top value. |
| `swap` | `a b -- b a` | Swap the top two values. |

## Instructions

### `vent <number>`

Pushes a number onto the stack.

```susm
vent 123
yap
```

Output:

```text
123
```

### `eject`

Pops and discards the top value.

```susm
vent 111
eject
vent 222
yap
```

Output:

```text
222
```

### `suspicious`

Adds the top two values.

```susm
vent 5
vent 7
suspicious
yap
```

Output:

```text
12
```

### `impostor`

Subtracts the top value from the value below it.

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

### `yap`

Prints the top value as a decimal number, followed by a newline.

```susm
vent 42
yap
```

### `yapc`

Prints the low byte of the top value as an ASCII character.

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

### `label <name>`

Defines a place that jumps can go to.

Label names must start with a letter or `_`, then use only letters, numbers, and `_`.

Good:

```susm
label loop
label _again
label room42
```

Bad:

```susm
label 42room
label sus-room
```

### `sus <name>`

Jumps to a label unconditionally.

```susm
label forever
sus forever
```

This creates an infinite loop.

### `sussy <name>`

Pops a value. If that value is not zero, jumps to the label.

```susm
vent 1
sussy somewhere
vent 999 # skipped

label somewhere
vent 42
yap
```

Output:

```text
42
```

### `dupe`

Duplicates the top value.

```susm
vent 7
dupe
suspicious
yap
```

Output:

```text
14
```

### `swap`

Swaps the top two values.

```susm
vent 3
vent 10
swap
impostor
yap
```

Output:

```text
7
```

Without `swap`, `impostor` would calculate `3 - 10`.

## Complete Examples

### Countdown

```susm
vent 3

label loop
dupe
yap
vent 1
impostor
dupe
sussy loop
eject
```

Output:

```text
3
2
1
```

## Common Errors

### Stack Underflow

This happens when an instruction needs a value, but the stack is empty.

```susm
yap
```

### Unknown Instruction

```susm
skibidi
```

### Missing Label

```susm
sus nowhere
```

### Duplicate Label

```susm
label loop
label loop
```
