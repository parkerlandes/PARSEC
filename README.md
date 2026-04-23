# PARSEC

*Parker's Simple Executable Code*

A small, hand-rolled interpreted language written in Python for CMSC 4513 — Programming Languages.

PARSEC is deliberately tiny: a single-file interpreter (`parsec.py`), a clean set of keywords and operators, and enough features to write real little programs. Source files are plain text (`.txt`) and are executed directly — no compilation step.

```parsec
let s = ask("Enter a word: ")
if s == reverse(s) {
    print s + " is a palindrome."
} else {
    print s + " is not a palindrome."
}
```

---

## Contents

- [Quick start](#quick-start)
- [Language reference](#language-reference)
  - [Values and types](#values-and-types)
  - [Variables](#variables)
  - [Output: `print`](#output-print)
  - [Input: `ask`](#input-ask)
  - [Operators](#operators)
  - [Conditionals: `if` / `else`](#conditionals-if--else)
  - [Loops: `loop` and `while`](#loops-loop-and-while)
  - [Built-in functions](#built-in-functions)
  - [Comments](#comments)
- [Full keyword and operator list](#full-keyword-and-operator-list)
- [Grammar](#grammar)
- [The seven example programs](#the-seven-example-programs)
- [Implementation notes](#implementation-notes)

---

## Quick start

Requirements: Python 3.8 or newer. No external packages.

Clone the repo and run any example:

```bash
python3 parsec.py programs/helloworld.txt
python3 parsec.py programs/multiply.txt
```

A program is just a text file. Pass its path as the single argument.

---

## Language reference

### Values and types

PARSEC has four value types:

| Type    | Examples                       |
|---------|--------------------------------|
| Number  | `0`, `42`, `-3`, `3.14`        |
| String  | `"hello"`, `""`, `"line 1\n"`  |
| Boolean | `true`, `false`                |
| (none)  | produced only by undefined vars (error) |

Strings support escapes `\n`, `\t`, `\"`, and `\\`.

Every value has a **truthiness** used by `if`, `while`, `and`, `or`, and `not`:

- `false`, `0`, `0.0`, and `""` are falsy.
- Everything else is truthy.

### Variables

Declare or reassign a variable with `let`:

```parsec
let x = 10
let name = "Ada"
let x = x + 1        // reassignment uses let again
```

Variables are global — PARSEC has no nested scopes. Using a variable that was never assigned is a runtime error.

### Output: `print`

`print` evaluates an expression and prints its string form followed by a newline.

```parsec
print "hi"
print 2 + 2            // prints 4
print "count: " + str(3)
```

When `+` has a string on either side, the other side is converted to a string. Otherwise `+` is numeric addition.

### Input: `ask`

`ask()` reads one line of input from the user and returns it as a **string** (no trailing newline).

```parsec
let name = ask()
let age  = ask("How old are you? ")
```

The optional argument is printed as a prompt (no added newline). Since `ask` always returns a string, convert to a number with `num(...)` when you need arithmetic:

```parsec
let n = num(ask("Enter a number: "))
print n * 2
```

### Operators

Arithmetic (numbers):

| Operator | Meaning                 |
|----------|-------------------------|
| `+`      | add (or concatenate, if either operand is a string) |
| `-`      | subtract (also unary negate) |
| `*`      | multiply                |
| `/`      | divide (returns a float if it doesn't divide evenly) |
| `%`      | modulo                  |

Comparison (returns boolean):

| Operator | Meaning                 |
|----------|-------------------------|
| `==`     | equal                   |
| `!=`     | not equal               |
| `<`      | less than               |
| `>`      | greater than            |
| `<=`     | less or equal           |
| `>=`     | greater or equal        |

Logical:

| Operator | Meaning                           |
|----------|-----------------------------------|
| `and`    | short-circuit AND                 |
| `or`     | short-circuit OR                  |
| `not`    | logical NOT                       |

Precedence, from lowest to highest:
`or` < `and` < `not` < comparisons < `+` `-` < `*` `/` `%` < unary `-` < primary.

Use parentheses to group.

### Conditionals: `if` / `else`

```parsec
if n % 2 == 0 {
    print "even"
} else {
    print "odd"
}
```

The `else` branch is optional. Every `if` body **must** be wrapped in braces `{ ... }`.

```parsec
if x > 0 {
    print "positive"
}
```

### Loops: `loop` and `while`

`loop` runs its body a fixed number of times:

```parsec
loop 5 {
    print "hi"
}
```

The count is evaluated once, when the loop begins. It must be a number; floats are truncated to integers.

`while` keeps running its body while the condition is truthy:

```parsec
let i = 1
while i <= 3 {
    print i
    let i = i + 1
}
```

Like `if`, both loops wrap their body in braces.

### Built-in functions

| Function    | What it does                                             |
|-------------|----------------------------------------------------------|
| `num(x)`    | Convert a string (or number) to a number. Errors on invalid input. |
| `str(x)`    | Convert any value to its string form.                    |
| `reverse(s)`| Return the string `s` reversed.                          |
| `length(s)` | Return the number of characters in `s`.                  |

### Comments

Anything from `//` to the end of the line is ignored:

```parsec
// this is a comment
let x = 1   // trailing comments work too
```

---

## Full keyword and operator list

**Keywords (12)**: `let`, `print`, `ask`, `if`, `else`, `loop`, `while`, `and`, `or`, `not`, `true`, `false`

**Operators (13)**: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `=`, unary `-`

**Punctuation**: `(`, `)`, `{`, `}`, `,`, `//`, `"`

**Built-ins (4)**: `num`, `str`, `reverse`, `length`

Total: well over the required 8 keywords/operators.

---

## Grammar

Informal BNF. Statement boundaries are newlines.

```
program     := statement*
statement   := let | print | if | loop | while | expr
let         := "let" IDENT "=" expression
print       := "print" expression
if          := "if" expression "{" block "}" ("else" "{" block "}")?
loop        := "loop" expression "{" block "}"
while       := "while" expression "{" block "}"

expression  := or_expr
or_expr     := and_expr ("or" and_expr)*
and_expr    := not_expr ("and" not_expr)*
not_expr    := "not" not_expr | comparison
comparison  := addition (("=="|"!="|"<"|">"|"<="|">=") addition)?
addition    := mult (("+"|"-") mult)*
mult        := unary (("*"|"/"|"%") unary)*
unary       := "-" unary | primary
primary     := NUMBER | STRING | "true" | "false"
             | "ask" "(" expression? ")"
             | IDENT "(" (expression ("," expression)*)? ")"
             | IDENT
             | "(" expression ")"
```

---

## The seven example programs

All live in `programs/`. Run any of them with `python3 parsec.py programs/<file>`.

### `helloworld.txt`

```parsec
print "Hello, World!"
```

### `cat.txt`

Reads one line and echoes it.

```parsec
let line = ask()
print line
```

### `multiply.txt`

Multiplies two single-digit numbers from the user.

```parsec
let a = num(ask("Enter the first digit: "))
let b = num(ask("Enter the second digit: "))
print a * b
```

### `repeater.txt`

Repeats a character a given number of times.

```parsec
let ch    = ask("Enter a character: ")
let times = num(ask("How many times?   "))

let out = ""
loop times {
    let out = out + ch
}
print out
```

### `reverse_string.txt`

```parsec
let s = ask("Enter a string: ")
print reverse(s)
```

### `is_palindrome.txt`

```parsec
let s = ask("Enter a string: ")
if s == reverse(s) {
    print s + " is a palindrome."
} else {
    print s + " is not a palindrome."
}
```

### `is_even.txt`

```parsec
let n = num(ask("Enter an integer: "))
if n % 2 == 0 {
    print n + " is even."
} else {
    print n + " is odd."
}
```

---

## Implementation notes

`parsec.py` is structured as three clearly separated stages:

1. **`tokenize(source)`** — a hand-written scanner that walks the source string character by character and produces a flat list of `Token` objects. It recognizes numbers, strings (with `\n`, `\t`, `\"`, `\\` escapes), identifiers, keywords, operators, parentheses, braces, commas, and newlines. Comments starting with `//` are stripped. It tracks line numbers for error messages.

2. **`Parser`** — a recursive-descent parser. Each grammar non-terminal is its own method (`parse_statement`, `parse_expression`, `parse_addition`, etc.), and precedence is baked into the call structure. The AST is represented as plain Python tuples of the form `(tag, child, child, ...)` — compact enough to print when debugging, and simple enough to pattern-match on.

3. **`Interpreter`** — a tree-walking evaluator. `execute` handles statements (`let`, `print`, `if`, `loop`, `while`, expression statements); `evaluate` handles expressions and returns Python values. Variables live in a single dict (`self.env`) — PARSEC has no nested scopes. Runtime problems (undefined variable, division by zero, bad `num()` input, type mismatches in arithmetic) raise `PARSECError`, which `main` catches and prints cleanly.

Why these design choices?

- **Single-file, no dependencies.** Easy to read, easy to grade, easy to hand to a classmate.
- **Tuple ASTs.** Keeps the parser under 150 lines. A bigger language would want real classes.
- **Global scope only.** The required programs don't need nested scopes or user-defined functions, and skipping them keeps the interpreter small without making the language feel toyish for these tasks.
- **Strings from `ask`, explicit `num()`.** Mirrors how Python's `input()` behaves and forces students writing in PARSEC to think about types.

---

## Project layout

```
PARSEC/
├── parsec.py                      # interpreter (lexer + parser + evaluator)
├── README.md                      # this file
├── programs/
│   ├── helloworld.txt
│   ├── cat.txt
│   ├── multiply.txt
│   ├── repeater.txt
│   ├── reverse_string.txt
│   ├── is_palindrome.txt
│   └── is_even.txt
└── transpiler/                    # PARSEC → C transpiler (Flex + Bison)
    ├── parsec.l                   # flex lexer
    ├── parsec.y                   # bison grammar with C emission
    ├── parsec_runtime.h           # runtime declarations
    ├── parsec_runtime.c           # runtime (pv type, arithmetic, I/O, etc.)
    └── Makefile
```

---

## Transpiler (PARSEC → C)

The `transpiler/` directory contains a PARSEC-to-C transpiler built with **Flex** and **Bison**. It reads a PARSEC `.txt` program and emits a C file that, once compiled, produces the same output as running the program through `parsec.py`.

### Requirements

- `flex` and `bison` (preinstalled on macOS with Xcode Command Line Tools; on Linux install the `flex` and `bison` packages)
- A C compiler (`cc` or `gcc`)

### How it works

- **`parsec.l`** defines the same tokens as the interpreter: keywords, operators, string/number literals, identifiers, braces, and `//` comments.
- **`parsec.y`** defines the PARSEC grammar. Each grammar rule has a semantic action in C. Expression actions build a *string of C source code* (e.g. the PARSEC expression `5 + 3` becomes the C expression `pv_add(pv_num(5), pv_num(3))`). Statement actions append C statements to a buffer. Variable names are collected into a set during parsing.
- After `yyparse()` finishes, the transpiler emits a complete `.c` file: `#include "parsec_runtime.h"`, then `int main(void) { ... }` containing the collected variable declarations followed by the buffered body.
- **`parsec_runtime.c`** provides a small runtime. A PARSEC value is represented by a tagged-union type `pv` (number, string, or bool). The runtime defines `pv_add`, `pv_sub`, `pv_eq`, `pv_lt`, `pv_print`, `pv_ask`, `pv_reverse`, `pv_length`, `pv_num_conv`, `pv_str_conv`, and `pv_truthy`. Short-circuit `and`/`or` are implemented as `PV_AND`/`PV_OR` macros using GCC statement expressions.

### Build and run

Build the transpiler binary and runtime:

```bash
cd transpiler
make
```

This produces `parsec2c` (the transpiler) and `parsec_runtime.o` (the precompiled runtime).

Transpile + compile + run a program in one step:

```bash
make run PROG=../programs/helloworld.txt
```

Or do the steps by hand:

```bash
./parsec2c ../programs/helloworld.txt > hello.c
cc -O2 hello.c parsec_runtime.o -o hello
./hello
```

### Example

The PARSEC program:

```parsec
let x = 5 + 3
print x
```

transpiles to:

```c
/* Auto-generated by parsec2c from ... */
#include "parsec_runtime.h"

int main(void) {
    pv x = pv_nil();
    x = pv_add(pv_num(5), pv_num(3));
    pv_print(x);
    return 0;
}
```

### Clean

```bash
make clean
```

Removes generated parser/lexer C, the transpiler binary, and any `_out.c` / `_out` artifacts from `make run`.
