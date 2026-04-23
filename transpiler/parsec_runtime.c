#include "parsec_runtime.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static void die(const char *msg) {
    fprintf(stderr, "PARSEC runtime error: %s\n", msg);
    exit(1);
}

static char *xstrdup(const char *s) {
    size_t n = strlen(s);
    char *p = (char *)malloc(n + 1);
    if (!p) die("out of memory");
    memcpy(p, s, n + 1);
    return p;
}

pv pv_nil(void) {
    pv v; v.type = PV_NIL; v.num = 0; v.str = NULL; v.boolean = false;
    return v;
}

pv pv_num(double n) {
    pv v = pv_nil();
    v.type = PV_NUM;
    v.num = n;
    return v;
}

pv pv_str(const char *s) {
    pv v = pv_nil();
    v.type = PV_STR;
    v.str = xstrdup(s);
    return v;
}

pv pv_bool(bool b) {
    pv v = pv_nil();
    v.type = PV_BOOL;
    v.boolean = b;
    return v;
}

static char *num_to_str(double n) {
    char buf[64];
    if (n == (long long)n) {
        snprintf(buf, sizeof buf, "%lld", (long long)n);
    } else {
        snprintf(buf, sizeof buf, "%g", n);
    }
    return xstrdup(buf);
}

static char *value_to_str(pv v) {
    switch (v.type) {
        case PV_NUM:  return num_to_str(v.num);
        case PV_STR:  return xstrdup(v.str ? v.str : "");
        case PV_BOOL: return xstrdup(v.boolean ? "true" : "false");
        default:      return xstrdup("");
    }
}

void pv_print(pv v) {
    char *s = value_to_str(v);
    puts(s);
    free(s);
}

pv pv_ask(pv prompt) {
    if (prompt.type != PV_NIL) {
        char *s = value_to_str(prompt);
        fputs(s, stdout);
        fflush(stdout);
        free(s);
    }
    size_t cap = 128, len = 0;
    char *buf = (char *)malloc(cap);
    if (!buf) die("out of memory");
    int c;
    while ((c = fgetc(stdin)) != EOF && c != '\n') {
        if (len + 1 >= cap) {
            cap *= 2;
            buf = (char *)realloc(buf, cap);
            if (!buf) die("out of memory");
        }
        buf[len++] = (char)c;
    }
    buf[len] = '\0';
    pv v = pv_str(buf);
    free(buf);
    return v;
}

bool pv_truthy(pv v) {
    switch (v.type) {
        case PV_BOOL: return v.boolean;
        case PV_NUM:  return v.num != 0.0;
        case PV_STR:  return v.str && v.str[0] != '\0';
        default:      return false;
    }
}

static bool both_num(pv a, pv b) {
    return a.type == PV_NUM && b.type == PV_NUM;
}

pv pv_add(pv a, pv b) {
    if (both_num(a, b)) return pv_num(a.num + b.num);
    char *sa = value_to_str(a);
    char *sb = value_to_str(b);
    size_t n = strlen(sa) + strlen(sb) + 1;
    char *out = (char *)malloc(n);
    if (!out) die("out of memory");
    strcpy(out, sa);
    strcat(out, sb);
    pv v = pv_str(out);
    free(sa); free(sb); free(out);
    return v;
}

pv pv_sub(pv a, pv b) {
    if (!both_num(a, b)) die("'-' requires numbers");
    return pv_num(a.num - b.num);
}

pv pv_mul(pv a, pv b) {
    if (!both_num(a, b)) die("'*' requires numbers");
    return pv_num(a.num * b.num);
}

pv pv_div(pv a, pv b) {
    if (!both_num(a, b)) die("'/' requires numbers");
    if (b.num == 0) die("division by zero");
    return pv_num(a.num / b.num);
}

pv pv_mod(pv a, pv b) {
    if (!both_num(a, b)) die("'%' requires numbers");
    if (b.num == 0) die("division by zero");
    return pv_num(fmod(a.num, b.num));
}

pv pv_neg(pv a) {
    if (a.type != PV_NUM) die("unary '-' requires a number");
    return pv_num(-a.num);
}

pv pv_eq(pv a, pv b) {
    if (a.type != b.type) return pv_bool(false);
    switch (a.type) {
        case PV_NUM:  return pv_bool(a.num == b.num);
        case PV_STR:  return pv_bool(strcmp(a.str, b.str) == 0);
        case PV_BOOL: return pv_bool(a.boolean == b.boolean);
        default:      return pv_bool(true);
    }
}

pv pv_ne(pv a, pv b) {
    pv r = pv_eq(a, b);
    r.boolean = !r.boolean;
    return r;
}

static void check_order(pv a, pv b) {
    if (a.type != b.type && !(a.type == PV_NUM && b.type == PV_NUM)) {
        die("cannot compare different types");
    }
}

pv pv_lt(pv a, pv b) {
    check_order(a, b);
    if (a.type == PV_NUM)  return pv_bool(a.num < b.num);
    if (a.type == PV_STR)  return pv_bool(strcmp(a.str, b.str) < 0);
    if (a.type == PV_BOOL) return pv_bool(a.boolean < b.boolean);
    return pv_bool(false);
}

pv pv_gt(pv a, pv b) {
    check_order(a, b);
    if (a.type == PV_NUM)  return pv_bool(a.num > b.num);
    if (a.type == PV_STR)  return pv_bool(strcmp(a.str, b.str) > 0);
    if (a.type == PV_BOOL) return pv_bool(a.boolean > b.boolean);
    return pv_bool(false);
}

pv pv_le(pv a, pv b) { pv r = pv_gt(a, b); r.boolean = !r.boolean; return r; }
pv pv_ge(pv a, pv b) { pv r = pv_lt(a, b); r.boolean = !r.boolean; return r; }

pv pv_not(pv a) { return pv_bool(!pv_truthy(a)); }

long pv_count(pv v) {
    if (v.type != PV_NUM) die("loop count must be a number");
    return (long)v.num;
}

pv pv_num_conv(pv v) {
    if (v.type == PV_NUM)  return v;
    if (v.type == PV_BOOL) return pv_num(v.boolean ? 1 : 0);
    if (v.type == PV_STR) {
        char *end = NULL;
        double d = strtod(v.str, &end);
        if (end == v.str) die("cannot convert string to number");
        while (*end == ' ' || *end == '\t') end++;
        if (*end != '\0') die("cannot convert string to number");
        return pv_num(d);
    }
    die("cannot convert to number");
    return pv_nil();
}

pv pv_str_conv(pv v) {
    char *s = value_to_str(v);
    pv out = pv_str(s);
    free(s);
    return out;
}

pv pv_reverse(pv v) {
    if (v.type != PV_STR) die("reverse() expects a string");
    size_t n = strlen(v.str);
    char *buf = (char *)malloc(n + 1);
    if (!buf) die("out of memory");
    for (size_t i = 0; i < n; i++) buf[i] = v.str[n - 1 - i];
    buf[n] = '\0';
    pv out = pv_str(buf);
    free(buf);
    return out;
}

pv pv_length(pv v) {
    if (v.type != PV_STR) die("length() expects a string");
    return pv_num((double)strlen(v.str));
}

/* ---- pointer wrappers used by the LLVM-IR codegen ---------------------- */

void pv_nil_p(pv *out)                          { *out = pv_nil(); }
void pv_num_p(pv *out, double n)                { *out = pv_num(n); }
void pv_str_p(pv *out, const char *s)           { *out = pv_str(s); }
void pv_bool_p(pv *out, bool b)                 { *out = pv_bool(b); }
void pv_assign(pv *dst, const pv *src)          { *dst = *src; }

void pv_print_p(const pv *v)                    { pv_print(*v); }
void pv_ask_p(pv *out, const pv *prompt)        { *out = pv_ask(*prompt); }

void pv_add_p(pv *out, const pv *a, const pv *b){ *out = pv_add(*a, *b); }
void pv_sub_p(pv *out, const pv *a, const pv *b){ *out = pv_sub(*a, *b); }
void pv_mul_p(pv *out, const pv *a, const pv *b){ *out = pv_mul(*a, *b); }
void pv_div_p(pv *out, const pv *a, const pv *b){ *out = pv_div(*a, *b); }
void pv_mod_p(pv *out, const pv *a, const pv *b){ *out = pv_mod(*a, *b); }
void pv_neg_p(pv *out, const pv *a)             { *out = pv_neg(*a); }

void pv_eq_p(pv *out, const pv *a, const pv *b) { *out = pv_eq(*a, *b); }
void pv_ne_p(pv *out, const pv *a, const pv *b) { *out = pv_ne(*a, *b); }
void pv_lt_p(pv *out, const pv *a, const pv *b) { *out = pv_lt(*a, *b); }
void pv_gt_p(pv *out, const pv *a, const pv *b) { *out = pv_gt(*a, *b); }
void pv_le_p(pv *out, const pv *a, const pv *b) { *out = pv_le(*a, *b); }
void pv_ge_p(pv *out, const pv *a, const pv *b) { *out = pv_ge(*a, *b); }

void pv_not_p(pv *out, const pv *a)             { *out = pv_not(*a); }
bool pv_truthy_p(const pv *v)                   { return pv_truthy(*v); }
long pv_count_p(const pv *v)                    { return pv_count(*v); }

void pv_num_conv_p(pv *out, const pv *v)        { *out = pv_num_conv(*v); }
void pv_str_conv_p(pv *out, const pv *v)        { *out = pv_str_conv(*v); }
void pv_reverse_p(pv *out, const pv *v)         { *out = pv_reverse(*v); }
void pv_length_p(pv *out, const pv *v)          { *out = pv_length(*v); }
