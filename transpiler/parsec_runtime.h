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

long pv_count(pv v);

pv pv_num_conv(pv v);
pv pv_str_conv(pv v);
pv pv_reverse(pv v);
pv pv_length(pv v);

#endif
