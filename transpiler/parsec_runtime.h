#ifndef PARSEC_RUNTIME_H
#define PARSEC_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>

typedef enum { PV_NIL, PV_NUM, PV_STR, PV_BOOL } pv_type;

typedef struct {
    pv_type type;
    double num;
    char *str;
    bool boolean;
} pv;

pv pv_nil(void);
pv pv_num(double n);
pv pv_str(const char *s);
pv pv_bool(bool b);

void pv_print(pv v);
pv pv_ask(pv prompt);

pv pv_add(pv a, pv b);
pv pv_sub(pv a, pv b);
pv pv_mul(pv a, pv b);
pv pv_div(pv a, pv b);
pv pv_mod(pv a, pv b);
pv pv_neg(pv a);

pv pv_eq(pv a, pv b);
pv pv_ne(pv a, pv b);
pv pv_lt(pv a, pv b);
pv pv_gt(pv a, pv b);
pv pv_le(pv a, pv b);
pv pv_ge(pv a, pv b);

pv pv_not(pv a);
bool pv_truthy(pv v);

/* Short-circuit and/or — use GCC/Clang statement expressions.
   Both operators return the value of whichever operand decided the result
   (matching PARSEC interpreter semantics), not a plain bool. */
#define PV_AND(a, b) ({ pv __pv_t = (a); pv_truthy(__pv_t) ? (b) : __pv_t; })
#define PV_OR(a, b)  ({ pv __pv_t = (a); pv_truthy(__pv_t) ? __pv_t : (b); })

/* ------------------------------------------------------------------------ */
/* Pointer-wrapper API used by the hand-written LLVM IR codegen.             */
/* These let generated IR pass `pv` values by pointer, sidestepping the       */
/* struct-by-value ABI differences between architectures.                    */
/* ------------------------------------------------------------------------ */

void pv_nil_p(pv *out);
void pv_num_p(pv *out, double n);
void pv_str_p(pv *out, const char *s);
void pv_bool_p(pv *out, bool b);
void pv_assign(pv *dst, const pv *src);

void pv_print_p(const pv *v);
void pv_ask_p(pv *out, const pv *prompt);

void pv_add_p(pv *out, const pv *a, const pv *b);
void pv_sub_p(pv *out, const pv *a, const pv *b);
void pv_mul_p(pv *out, const pv *a, const pv *b);
void pv_div_p(pv *out, const pv *a, const pv *b);
void pv_mod_p(pv *out, const pv *a, const pv *b);
void pv_neg_p(pv *out, const pv *a);

void pv_eq_p(pv *out, const pv *a, const pv *b);
void pv_ne_p(pv *out, const pv *a, const pv *b);
void pv_lt_p(pv *out, const pv *a, const pv *b);
void pv_gt_p(pv *out, const pv *a, const pv *b);
void pv_le_p(pv *out, const pv *a, const pv *b);
void pv_ge_p(pv *out, const pv *a, const pv *b);

void pv_not_p(pv *out, const pv *a);
bool pv_truthy_p(const pv *v);
long pv_count_p(const pv *v);

void pv_num_conv_p(pv *out, const pv *v);
void pv_str_conv_p(pv *out, const pv *v);
void pv_reverse_p(pv *out, const pv *v);
void pv_length_p(pv *out, const pv *v);

long pv_count(pv v);

pv pv_num_conv(pv v);
pv pv_str_conv(pv v);
pv pv_reverse(pv v);
pv pv_length(pv v);

#endif
