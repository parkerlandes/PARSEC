#!/usr/bin/env python3
"""
PARSEC LLVM compiler — emits LLVM IR from PARSEC source.

Usage:
    python3 parsec_llvm.py <program.txt> > program.ll
    clang program.ll transpiler/parsec_runtime.c -o program
    ./program

Re-uses the lexer and parser from parsec.py. Walks the AST and emits
LLVM IR text in the opaque-pointer form used by LLVM 15+.
"""

import sys

from parsec import tokenize, Parser


PV_STRUCT = "{ i32, double, ptr, i8 }"


def encode_ll_string(s):
    """Return (IR-escaped body, byte length including null terminator)."""
    b = s.encode("utf-8")
    out = []
    for byte in b:
        if 32 <= byte <= 126 and byte != ord('"') and byte != ord("\\"):
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:02X}")
    out.append("\\00")
    return "".join(out), len(b) + 1


BINOP_FN = {
    "+":  "pv_add_p",
    "-":  "pv_sub_p",
    "*":  "pv_mul_p",
    "/":  "pv_div_p",
    "%":  "pv_mod_p",
    "==": "pv_eq_p",
    "!=": "pv_ne_p",
    "<":  "pv_lt_p",
    ">":  "pv_gt_p",
    "<=": "pv_le_p",
    ">=": "pv_ge_p",
}


CALL_FN = {
    "num":     "pv_num_conv_p",
    "str":     "pv_str_conv_p",
    "reverse": "pv_reverse_p",
    "length":  "pv_length_p",
}


class LLVMGen:
    def __init__(self):
        self.body = []
        self.strings = []         # list of (label, encoded_body, byte_len)
        self.string_cache = {}    # python_string -> index into self.strings
        self.variables = []       # ordered list of PARSEC variable names
        self.var_set = set()
        self.allocas = []         # list of (name, "pv" | "i64")
        self.temp_num = 0
        self.label_num = 0

    def new_pv_slot(self):
        name = f"%t{self.temp_num}"
        self.temp_num += 1
        self.allocas.append((name, "pv"))
        return name

    def new_i64_slot(self):
        name = f"%i{self.temp_num}"
        self.temp_num += 1
        self.allocas.append((name, "i64"))
        return name

    def new_scalar(self):
        name = f"%s{self.temp_num}"
        self.temp_num += 1
        return name

    def new_label(self):
        name = f"L{self.label_num}"
        self.label_num += 1
        return name

    def emit(self, s):
        self.body.append(s)

    def add_string(self, s):
        if s not in self.string_cache:
            idx = len(self.strings)
            self.string_cache[s] = idx
            encoded, byte_len = encode_ll_string(s)
            self.strings.append((f"@.str.{idx}", encoded, byte_len))
        return self.strings[self.string_cache[s]]

    def declare_var(self, name):
        if name not in self.var_set:
            self.var_set.add(name)
            self.variables.append(name)

    # ----- expressions ------------------------------------------------

    def gen_expr(self, node):
        kind = node[0]

        if kind == "number":
            t = self.new_pv_slot()
            self.emit(f"  call void @pv_num_p(ptr {t}, double {repr(float(node[1]))})")
            return t

        if kind == "string":
            label, _, _ = self.add_string(node[1])
            t = self.new_pv_slot()
            self.emit(f"  call void @pv_str_p(ptr {t}, ptr {label})")
            return t

        if kind == "bool":
            t = self.new_pv_slot()
            self.emit(f"  call void @pv_bool_p(ptr {t}, i1 {1 if node[1] else 0})")
            return t

        if kind == "var":
            self.declare_var(node[1])
            return f"%var.{node[1]}"

        if kind == "neg":
            a = self.gen_expr(node[1])
            t = self.new_pv_slot()
            self.emit(f"  call void @pv_neg_p(ptr {t}, ptr {a})")
            return t

        if kind == "not":
            a = self.gen_expr(node[1])
            t = self.new_pv_slot()
            self.emit(f"  call void @pv_not_p(ptr {t}, ptr {a})")
            return t

        if kind == "binop":
            op = node[1]
            left = self.gen_expr(node[2])
            right = self.gen_expr(node[3])
            t = self.new_pv_slot()
            self.emit(f"  call void @{BINOP_FN[op]}(ptr {t}, ptr {left}, ptr {right})")
            return t

        if kind == "and":
            return self._gen_short_circuit(node[1], node[2], and_mode=True)

        if kind == "or":
            return self._gen_short_circuit(node[1], node[2], and_mode=False)

        if kind == "ask":
            t = self.new_pv_slot()
            if node[1] is None:
                nil_slot = self.new_pv_slot()
                self.emit(f"  call void @pv_nil_p(ptr {nil_slot})")
                self.emit(f"  call void @pv_ask_p(ptr {t}, ptr {nil_slot})")
            else:
                prompt = self.gen_expr(node[1])
                self.emit(f"  call void @pv_ask_p(ptr {t}, ptr {prompt})")
            return t

        if kind == "call":
            name = node[1]
            args = [self.gen_expr(a) for a in node[2]]
            fn = CALL_FN.get(name)
            if fn is None:
                raise SyntaxError(f"Unknown function: {name}")
            t = self.new_pv_slot()
            arg_parts = ", ".join(f"ptr {a}" for a in args)
            self.emit(f"  call void @{fn}(ptr {t}, {arg_parts})")
            return t

        raise Exception(f"gen_expr: unknown node kind {kind}")

    def _gen_short_circuit(self, left_node, right_node, and_mode):
        """Generate short-circuit AND (and_mode=True) or OR (and_mode=False)."""
        left = self.gen_expr(left_node)
        truthy = self.new_scalar()
        self.emit(f"  {truthy} = call i1 @pv_truthy_p(ptr {left})")
        lbl_eval_right = self.new_label()
        lbl_use_left = self.new_label()
        lbl_end = self.new_label()
        result = self.new_pv_slot()
        # AND: truthy -> eval right; falsy -> use left.
        # OR:  truthy -> use left;   falsy -> eval right.
        if and_mode:
            t_label, f_label = lbl_eval_right, lbl_use_left
        else:
            t_label, f_label = lbl_use_left, lbl_eval_right
        self.emit(f"  br i1 {truthy}, label %{t_label}, label %{f_label}")

        self.emit(f"{lbl_eval_right}:")
        right = self.gen_expr(right_node)
        self.emit(f"  call void @pv_assign(ptr {result}, ptr {right})")
        self.emit(f"  br label %{lbl_end}")

        self.emit(f"{lbl_use_left}:")
        self.emit(f"  call void @pv_assign(ptr {result}, ptr {left})")
        self.emit(f"  br label %{lbl_end}")

        self.emit(f"{lbl_end}:")
        return result

    # ----- statements -------------------------------------------------

    def gen_stmt(self, node):
        kind = node[0]

        if kind == "block":
            for s in node[1]:
                self.gen_stmt(s)
            return

        if kind == "let":
            _, name, expr = node
            self.declare_var(name)
            val = self.gen_expr(expr)
            self.emit(f"  call void @pv_assign(ptr %var.{name}, ptr {val})")
            return

        if kind == "print":
            val = self.gen_expr(node[1])
            self.emit(f"  call void @pv_print_p(ptr {val})")
            return

        if kind == "if":
            _, cond, then_block, else_block = node
            cval = self.gen_expr(cond)
            truthy = self.new_scalar()
            self.emit(f"  {truthy} = call i1 @pv_truthy_p(ptr {cval})")
            lbl_then = self.new_label()
            lbl_else = self.new_label()
            lbl_end = self.new_label()
            self.emit(f"  br i1 {truthy}, label %{lbl_then}, label %{lbl_else}")
            self.emit(f"{lbl_then}:")
            self.gen_stmt(then_block)
            self.emit(f"  br label %{lbl_end}")
            self.emit(f"{lbl_else}:")
            self.gen_stmt(else_block)
            self.emit(f"  br label %{lbl_end}")
            self.emit(f"{lbl_end}:")
            return

        if kind == "loop":
            _, count_expr, body = node
            cval = self.gen_expr(count_expr)
            count_reg = self.new_scalar()
            self.emit(f"  {count_reg} = call i64 @pv_count_p(ptr {cval})")
            idx_slot = self.new_i64_slot()
            self.emit(f"  store i64 0, ptr {idx_slot}")
            lbl_cond = self.new_label()
            lbl_body = self.new_label()
            lbl_end = self.new_label()
            self.emit(f"  br label %{lbl_cond}")
            self.emit(f"{lbl_cond}:")
            idx_cur = self.new_scalar()
            self.emit(f"  {idx_cur} = load i64, ptr {idx_slot}")
            cmp = self.new_scalar()
            self.emit(f"  {cmp} = icmp slt i64 {idx_cur}, {count_reg}")
            self.emit(f"  br i1 {cmp}, label %{lbl_body}, label %{lbl_end}")
            self.emit(f"{lbl_body}:")
            self.gen_stmt(body)
            idx_inc = self.new_scalar()
            self.emit(f"  {idx_inc} = add i64 {idx_cur}, 1")
            self.emit(f"  store i64 {idx_inc}, ptr {idx_slot}")
            self.emit(f"  br label %{lbl_cond}")
            self.emit(f"{lbl_end}:")
            return

        if kind == "while":
            _, cond, body = node
            lbl_cond = self.new_label()
            lbl_body = self.new_label()
            lbl_end = self.new_label()
            self.emit(f"  br label %{lbl_cond}")
            self.emit(f"{lbl_cond}:")
            cval = self.gen_expr(cond)
            truthy = self.new_scalar()
            self.emit(f"  {truthy} = call i1 @pv_truthy_p(ptr {cval})")
            self.emit(f"  br i1 {truthy}, label %{lbl_body}, label %{lbl_end}")
            self.emit(f"{lbl_body}:")
            self.gen_stmt(body)
            self.emit(f"  br label %{lbl_cond}")
            self.emit(f"{lbl_end}:")
            return

        if kind == "expr":
            self.gen_expr(node[1])
            return

        raise Exception(f"gen_stmt: unknown node kind {kind}")

    # ----- finalize ---------------------------------------------------

    def output(self, source_path):
        out = []
        out.append(f"; Compiled by parsec_llvm.py from {source_path}")
        out.append(f"%pv = type {PV_STRUCT}")
        out.append("")

        for label, encoded, byte_len in self.strings:
            out.append(f'{label} = private unnamed_addr constant [{byte_len} x i8] c"{encoded}"')
        if self.strings:
            out.append("")

        out.append("declare void @pv_nil_p(ptr)")
        out.append("declare void @pv_num_p(ptr, double)")
        out.append("declare void @pv_str_p(ptr, ptr)")
        out.append("declare void @pv_bool_p(ptr, i1)")
        out.append("declare void @pv_assign(ptr, ptr)")
        out.append("declare void @pv_print_p(ptr)")
        out.append("declare void @pv_ask_p(ptr, ptr)")
        for fn in sorted(set(BINOP_FN.values())):
            out.append(f"declare void @{fn}(ptr, ptr, ptr)")
        out.append("declare void @pv_neg_p(ptr, ptr)")
        out.append("declare void @pv_not_p(ptr, ptr)")
        out.append("declare i1 @pv_truthy_p(ptr)")
        out.append("declare i64 @pv_count_p(ptr)")
        for fn in sorted(set(CALL_FN.values())):
            out.append(f"declare void @{fn}(ptr, ptr)")
        out.append("")

        out.append("define i32 @main() {")
        out.append("entry:")
        for v in self.variables:
            out.append(f"  %var.{v} = alloca %pv")
            out.append(f"  call void @pv_nil_p(ptr %var.{v})")
        for name, ty in self.allocas:
            llvm_ty = "%pv" if ty == "pv" else "i64"
            out.append(f"  {name} = alloca {llvm_ty}")
        out.extend(self.body)
        out.append("  ret i32 0")
        out.append("}")
        out.append("")
        return "\n".join(out)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 parsec_llvm.py <program.txt>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r") as f:
            source = f.read()
    except OSError as e:
        print(f"Cannot open {path}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        tokens = tokenize(source)
        ast = Parser(tokens).parse()
        gen = LLVMGen()
        gen.gen_stmt(ast)
        sys.stdout.write(gen.output(path))
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
