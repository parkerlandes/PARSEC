#!/usr/bin/env python3
"""
Language features:
    let x = expr            // variable assignment
    print expr              // print a value, followed by newline
    ask()                   // read a line of input, returns a string
    ask("prompt: ")         // read input with a prompt
    if cond { ... } else { ... }
    loop N { ... }          // loop body N times
    while cond { ... }      // loop while cond is truthy

Built-in functions:
    num(x)        convert string to number
    str(x)        convert anything to string
    reverse(s)    reverse a string
    length(s)     length of a string

Operators:
    + - * / %                arithmetic (+ also concatenates strings)
    == != < > <= >=          comparison
    and  or  not             logical

This file contains three stages, in order:
    1. tokenize()   - turns source text into a flat list of tokens
    2. Parser       - turns tokens into an abstract syntax tree (AST)
    3. Interpreter  - walks the AST and executes the program
"""

import sys


# =============================================================================
# 1. LEXER
# =============================================================================

# Words the lexer treats as keywords rather than identifiers.
KEYWORDS = {
    "let", "print", "ask",
    "if", "else",
    "loop", "while",
    "and", "or", "not",
    "true", "false",
}


class Token:
    """A single lexical token: a type tag, a value, and the source line."""

    __slots__ = ("type", "value", "line")

    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


def tokenize(source):
    """Convert raw source text into a list of Token objects."""
    tokens = []
    line = 1
    i = 0
    n = len(source)

    while i < n:
        c = source[i]

        # --- whitespace (spaces/tabs are insignificant; newlines matter) ---
        if c == " " or c == "\t" or c == "\r":
            i += 1
            continue

        if c == "\n":
            tokens.append(Token("NEWLINE", "\n", line))
            line += 1
            i += 1
            continue

        # --- comments run to end of line ---
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue

        # --- string literals, with a few standard escapes ---
        if c == '"':
            i += 1
            buf = []
            while i < n and source[i] != '"':
                if source[i] == "\\" and i + 1 < n:
                    esc = source[i + 1]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
                    i += 2
                else:
                    if source[i] == "\n":
                        line += 1
                    buf.append(source[i])
                    i += 1
            if i >= n:
                raise SyntaxError(f"Unterminated string on line {line}")
            tokens.append(Token("STRING", "".join(buf), line))
            i += 1  # closing quote
            continue

        # --- numbers (integer or float) ---
        if c.isdigit():
            start = i
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == "." and i + 1 < n and source[i + 1].isdigit():
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
                tokens.append(Token("NUMBER", float(source[start:i]), line))
            else:
                tokens.append(Token("NUMBER", int(source[start:i]), line))
            continue

        # --- identifiers and keywords ---
        if c.isalpha() or c == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            if word == "true":
                tokens.append(Token("BOOL", True, line))
            elif word == "false":
                tokens.append(Token("BOOL", False, line))
            elif word in KEYWORDS:
                tokens.append(Token(word.upper(), word, line))
            else:
                tokens.append(Token("IDENT", word, line))
            continue

        # --- two-character operators first, then one-character ---
        two = source[i:i + 2]
        if two in ("==", "!=", "<=", ">="):
            tokens.append(Token("OP", two, line))
            i += 2
            continue

        if c in "+-*/%<>=":
            tokens.append(Token("OP", c, line))
            i += 1
            continue

        if c == "(":
            tokens.append(Token("LPAREN", "(", line))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", ")", line))
            i += 1
            continue
        if c == ",":
            tokens.append(Token("COMMA", ",", line))
            i += 1
            continue
        if c == "{":
            tokens.append(Token("LBRACE", "{", line))
            i += 1
            continue
        if c == "}":
            tokens.append(Token("RBRACE", "}", line))
            i += 1
            continue

        raise SyntaxError(f"Unexpected character {c!r} on line {line}")

    tokens.append(Token("EOF", None, line))
    return tokens


# =============================================================================
# 2. PARSER
# =============================================================================
#
# The parser is a hand-written recursive-descent parser. AST nodes are plain
# tuples whose first element is a tag string, which keeps the code compact and
# easy to follow.
#
# Grammar (informal):
#
#   program     := statement*
#   statement   := let | print | if | loop | while | expr
#   let         := 'let' IDENT '=' expression
#   print       := 'print' expression
#   if          := 'if' expression '{' block '}' ('else' '{' block '}')?
#   loop        := 'loop' expression '{' block '}'
#   while       := 'while' expression '{' block '}'
#
#   expression  := or_expr
#   or_expr     := and_expr ('or' and_expr)*
#   and_expr    := not_expr ('and' not_expr)*
#   not_expr    := 'not' not_expr | comparison
#   comparison  := addition (('=='|'!='|'<'|'>'|'<='|'>=') addition)?
#   addition    := mult (('+'|'-') mult)*
#   mult        := unary (('*'|'/'|'%') unary)*
#   unary       := '-' unary | primary
#   primary     := NUMBER | STRING | BOOL | IDENT | 'ask' '(' expr? ')'
#                 | IDENT '(' args? ')' | '(' expression ')'

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---- helpers ---------------------------------------------------------

    def peek(self, offset=0):
        return self.tokens[self.pos + offset]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, type_, value=None):
        tok = self.peek()
        if tok.type != type_ or (value is not None and tok.value != value):
            wanted = f"{type_}" + (f" {value!r}" if value is not None else "")
            raise SyntaxError(
                f"Expected {wanted} but got {tok.type} {tok.value!r} on line {tok.line}"
            )
        return self.advance()

    def skip_newlines(self):
        while self.peek().type == "NEWLINE":
            self.advance()

    # ---- top-level -------------------------------------------------------

    def parse(self):
        self.skip_newlines()
        stmts = []
        while self.peek().type != "EOF":
            stmts.append(self.parse_statement())
            self.skip_newlines()
        return ("block", stmts)

    def parse_block(self, terminators):
        """Parse statements until we hit a terminator token (RBRACE/EOF)."""
        self.skip_newlines()
        stmts = []
        while self.peek().type != "EOF" and self.peek().type not in terminators:
            stmts.append(self.parse_statement())
            self.skip_newlines()
        return ("block", stmts)

    # ---- statements ------------------------------------------------------

    def parse_statement(self):
        t = self.peek().type
        if t == "LET":
            return self.parse_let()
        if t == "PRINT":
            return self.parse_print()
        if t == "IF":
            return self.parse_if()
        if t == "LOOP":
            return self.parse_loop()
        if t == "WHILE":
            return self.parse_while()
        # Bare expression, e.g. a function call used for side effects.
        return ("expr", self.parse_expression())

    def parse_let(self):
        self.expect("LET")
        name = self.expect("IDENT").value
        self.expect("OP", "=")
        return ("let", name, self.parse_expression())

    def parse_print(self):
        self.expect("PRINT")
        return ("print", self.parse_expression())

    def parse_if(self):
        self.expect("IF")
        cond = self.parse_expression()
        self.expect("LBRACE")
        then_block = self.parse_block({"RBRACE"})
        self.expect("RBRACE")
        else_block = ("block", [])
        self.skip_newlines()
        if self.peek().type == "ELSE":
            self.advance()
            self.expect("LBRACE")
            else_block = self.parse_block({"RBRACE"})
            self.expect("RBRACE")
        return ("if", cond, then_block, else_block)

    def parse_loop(self):
        self.expect("LOOP")
        count = self.parse_expression()
        self.expect("LBRACE")
        body = self.parse_block({"RBRACE"})
        self.expect("RBRACE")
        return ("loop", count, body)

    def parse_while(self):
        self.expect("WHILE")
        cond = self.parse_expression()
        self.expect("LBRACE")
        body = self.parse_block({"RBRACE"})
        self.expect("RBRACE")
        return ("while", cond, body)

    # ---- expressions (precedence climbs from low to high) ---------------

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.peek().type == "OR":
            self.advance()
            left = ("or", left, self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek().type == "AND":
            self.advance()
            left = ("and", left, self.parse_not())
        return left

    def parse_not(self):
        if self.peek().type == "NOT":
            self.advance()
            return ("not", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_addition()
        tok = self.peek()
        if tok.type == "OP" and tok.value in ("==", "!=", "<", ">", "<=", ">="):
            op = self.advance().value
            right = self.parse_addition()
            left = ("binop", op, left, right)
        return left

    def parse_addition(self):
        left = self.parse_mult()
        while self.peek().type == "OP" and self.peek().value in ("+", "-"):
            op = self.advance().value
            left = ("binop", op, left, self.parse_mult())
        return left

    def parse_mult(self):
        left = self.parse_unary()
        while self.peek().type == "OP" and self.peek().value in ("*", "/", "%"):
            op = self.advance().value
            left = ("binop", op, left, self.parse_unary())
        return left

    def parse_unary(self):
        if self.peek().type == "OP" and self.peek().value == "-":
            self.advance()
            return ("neg", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()

        if tok.type == "NUMBER":
            self.advance()
            return ("number", tok.value)

        if tok.type == "STRING":
            self.advance()
            return ("string", tok.value)

        if tok.type == "BOOL":
            self.advance()
            return ("bool", tok.value)

        if tok.type == "LPAREN":
            self.advance()
            expr = self.parse_expression()
            self.expect("RPAREN")
            return expr

        if tok.type == "ASK":
            self.advance()
            self.expect("LPAREN")
            if self.peek().type == "RPAREN":
                self.advance()
                return ("ask", None)
            prompt = self.parse_expression()
            self.expect("RPAREN")
            return ("ask", prompt)

        if tok.type == "IDENT":
            self.advance()
            # Function call: IDENT(args)
            if self.peek().type == "LPAREN":
                self.advance()
                args = []
                if self.peek().type != "RPAREN":
                    args.append(self.parse_expression())
                    while self.peek().type == "COMMA":
                        self.advance()
                        args.append(self.parse_expression())
                self.expect("RPAREN")
                return ("call", tok.value, args)
            # Otherwise a bare variable reference.
            return ("var", tok.value)

        raise SyntaxError(
            f"Unexpected token {tok.type} {tok.value!r} on line {tok.line}"
        )


# =============================================================================
# 3. INTERPRETER
# =============================================================================

class PARSECError(Exception):
    """A runtime error inside a PARSEC program."""


class Interpreter:
    def __init__(self):
        self.env = {}
        self.builtins = {
            "num": self._num,
            "str": self._str,
            "reverse": self._reverse,
            "length": self._length,
        }

    # ---- built-in functions ---------------------------------------------

    def _num(self, args):
        if len(args) != 1:
            raise PARSECError("num() takes exactly 1 argument")
        v = args[0]
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, (int, float)):
            return v
        try:
            s = str(v).strip()
            if "." in s:
                return float(s)
            return int(s)
        except ValueError:
            raise PARSECError(f"Cannot convert {v!r} to a number")

    def _str(self, args):
        if len(args) != 1:
            raise PARSECError("str() takes exactly 1 argument")
        return self._to_string(args[0])

    def _reverse(self, args):
        if len(args) != 1:
            raise PARSECError("reverse() takes exactly 1 argument")
        if not isinstance(args[0], str):
            raise PARSECError("reverse() expects a string")
        return args[0][::-1]

    def _length(self, args):
        if len(args) != 1:
            raise PARSECError("length() takes exactly 1 argument")
        if not isinstance(args[0], str):
            raise PARSECError("length() expects a string")
        return len(args[0])

    # ---- value helpers ---------------------------------------------------

    def _to_string(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _is_truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return value is not None

    # ---- statement execution --------------------------------------------

    def execute(self, node):
        kind = node[0]

        if kind == "block":
            for stmt in node[1]:
                self.execute(stmt)
            return

        if kind == "let":
            _, name, expr = node
            self.env[name] = self.evaluate(expr)
            return

        if kind == "print":
            print(self._to_string(self.evaluate(node[1])))
            return

        if kind == "if":
            _, cond, then_block, else_block = node
            if self._is_truthy(self.evaluate(cond)):
                self.execute(then_block)
            else:
                self.execute(else_block)
            return

        if kind == "loop":
            count = self.evaluate(node[1])
            if isinstance(count, float):
                count = int(count)
            if not isinstance(count, int):
                raise PARSECError("loop count must be a number")
            for _ in range(count):
                self.execute(node[2])
            return

        if kind == "while":
            while self._is_truthy(self.evaluate(node[1])):
                self.execute(node[2])
            return

        if kind == "expr":
            self.evaluate(node[1])
            return

        raise PARSECError(f"Internal: unknown statement {kind}")

    # ---- expression evaluation ------------------------------------------

    def evaluate(self, node):
        kind = node[0]

        if kind == "number" or kind == "string" or kind == "bool":
            return node[1]

        if kind == "var":
            name = node[1]
            if name not in self.env:
                raise PARSECError(f"Undefined variable: {name}")
            return self.env[name]

        if kind == "neg":
            v = self.evaluate(node[1])
            if not isinstance(v, (int, float)):
                raise PARSECError("Unary '-' requires a number")
            return -v

        if kind == "not":
            return not self._is_truthy(self.evaluate(node[1]))

        if kind == "and":
            left = self.evaluate(node[1])
            if not self._is_truthy(left):
                return left
            return self.evaluate(node[2])

        if kind == "or":
            left = self.evaluate(node[1])
            if self._is_truthy(left):
                return left
            return self.evaluate(node[2])

        if kind == "binop":
            _, op, left_node, right_node = node
            return self._binop(op, self.evaluate(left_node), self.evaluate(right_node))

        if kind == "ask":
            prompt = self.evaluate(node[1]) if node[1] is not None else ""
            return input(self._to_string(prompt))

        if kind == "call":
            _, name, arg_nodes = node
            args = [self.evaluate(a) for a in arg_nodes]
            if name in self.builtins:
                return self.builtins[name](args)
            raise PARSECError(f"Unknown function: {name}")

        raise PARSECError(f"Internal: unknown expression {kind}")

    def _binop(self, op, left, right):
        # '+' is overloaded: number + number -> number, otherwise concatenate as strings.
        if op == "+":
            if isinstance(left, (int, float)) and isinstance(right, (int, float)) \
                    and not isinstance(left, bool) and not isinstance(right, bool):
                return left + right
            return self._to_string(left) + self._to_string(right)

        if op in ("-", "*", "/", "%"):
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                raise PARSECError(f"Operator {op!r} requires numbers")
            if op == "-": return left - right
            if op == "*": return left * right
            if op == "/":
                if right == 0:
                    raise PARSECError("Division by zero")
                return left / right
            if op == "%":
                if right == 0:
                    raise PARSECError("Division by zero")
                return left % right

        if op == "==": return left == right
        if op == "!=": return left != right
        if op in ("<", ">", "<=", ">="):
            # Only compare like-typed ordered values.
            if type(left) is not type(right) and not (
                isinstance(left, (int, float)) and isinstance(right, (int, float))
            ):
                raise PARSECError(f"Cannot compare {type(left).__name__} and {type(right).__name__}")
            if op == "<": return left < right
            if op == ">": return left > right
            if op == "<=": return left <= right
            if op == ">=": return left >= right

        raise PARSECError(f"Unknown operator: {op}")


# =============================================================================
# 4. DRIVER
# =============================================================================

def run(source):
    tokens = tokenize(source)
    ast = Parser(tokens).parse()
    Interpreter().execute(ast)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parsec.py <program.txt>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r") as f:
            source = f.read()
    except OSError as e:
        print(f"Cannot open {path}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        run(source)
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)
    except PARSECError as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
