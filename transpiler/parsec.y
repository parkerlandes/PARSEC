%error-verbose

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

extern int   yylex(void);
extern FILE *yyin;
extern int   yylineno_;
void yyerror(const char *msg);

/* ---- variable set -------------------------------------------------------- */

#define MAX_VARS 512
static char *declared_vars[MAX_VARS];
static int   declared_count = 0;

static void declare_var(const char *name) {
    for (int i = 0; i < declared_count; i++) {
        if (strcmp(declared_vars[i], name) == 0) return;
    }
    if (declared_count >= MAX_VARS) {
        fprintf(stderr, "Too many variables\n");
        exit(1);
    }
    declared_vars[declared_count++] = strdup(name);
}

/* ---- body buffer --------------------------------------------------------- */

static char  *body_buf = NULL;
static size_t body_len = 0;
static size_t body_cap = 0;

static void emit(const char *fmt, ...) {
    va_list ap, ap2;
    va_start(ap, fmt);
    va_copy(ap2, ap);
    int need = vsnprintf(NULL, 0, fmt, ap2);
    va_end(ap2);
    while (body_len + need + 1 > body_cap) {
        body_cap = body_cap ? body_cap * 2 : 1024;
        body_buf = (char *)realloc(body_buf, body_cap);
        if (!body_buf) { perror("realloc"); exit(1); }
    }
    vsnprintf(body_buf + body_len, body_cap - body_len, fmt, ap);
    body_len += need;
    va_end(ap);
}

/* ---- string helpers ------------------------------------------------------ */

static char *fmtstr(const char *fmt, ...) {
    va_list ap, ap2;
    va_start(ap, fmt);
    va_copy(ap2, ap);
    int n = vsnprintf(NULL, 0, fmt, ap2);
    va_end(ap2);
    char *s = (char *)malloc(n + 1);
    if (!s) { perror("malloc"); exit(1); }
    vsnprintf(s, n + 1, fmt, ap);
    va_end(ap);
    return s;
}

static char *mk1(const char *fn, char *a) {
    char *r = fmtstr("%s(%s)", fn, a);
    free(a);
    return r;
}

static char *mk2(const char *fn, char *a, char *b) {
    char *r = fmtstr("%s(%s, %s)", fn, a, b);
    free(a); free(b);
    return r;
}

static char *emit_call(char *name, char *args) {
    const char *c_name = NULL;
    if      (strcmp(name, "num")     == 0) c_name = "pv_num_conv";
    else if (strcmp(name, "str")     == 0) c_name = "pv_str_conv";
    else if (strcmp(name, "reverse") == 0) c_name = "pv_reverse";
    else if (strcmp(name, "length")  == 0) c_name = "pv_length";
    else {
        fprintf(stderr, "Unknown function: %s\n", name);
        exit(1);
    }
    char *r = fmtstr("%s(%s)", c_name, args ? args : "");
    free(name);
    if (args) free(args);
    return r;
}
%}

%union {
    char *sval;
}

%token <sval> NUMBER STRING IDENT BOOLLIT
%token LET PRINT ASK IF ELSE LOOP WHILE AND OR NOT
%token EQ NE LT GT LE GE

%type <sval> expr primary args

%left  OR
%left  AND
%right NOT
%nonassoc EQ NE LT GT LE GE
%left  '+' '-'
%left  '*' '/' '%'
%right UMINUS

%start program

%%

program : stmts
        ;

stmts   : /* empty */
        | stmts stmt
        ;

stmt    : LET IDENT '=' expr
            { declare_var($2); emit("    %s = %s;\n", $2, $4); free($2); free($4); }
        | PRINT expr
            { emit("    pv_print(%s);\n", $2); free($2); }
        | if_stmt
        | loop_stmt
        | while_stmt
        | expr
            { emit("    (void)%s;\n", $1); free($1); }
        ;

if_stmt : IF expr '{'
            { emit("    if (pv_truthy(%s)) {\n", $2); free($2); }
          stmts '}'
            { emit("    }\n"); }
          else_opt
        ;

else_opt: /* empty */
        | ELSE '{'
            { emit("    else {\n"); }
          stmts '}'
            { emit("    }\n"); }
        ;

loop_stmt : LOOP expr '{'
              { emit("    { long __c = pv_count(%s); for (long __i = 0; __i < __c; __i++) {\n", $2); free($2); }
            stmts '}'
              { emit("    } }\n"); }
          ;

while_stmt : WHILE expr '{'
               { emit("    while (pv_truthy(%s)) {\n", $2); free($2); }
             stmts '}'
               { emit("    }\n"); }
           ;

expr    : expr '+' expr   { $$ = mk2("pv_add", $1, $3); }
        | expr '-' expr   { $$ = mk2("pv_sub", $1, $3); }
        | expr '*' expr   { $$ = mk2("pv_mul", $1, $3); }
        | expr '/' expr   { $$ = mk2("pv_div", $1, $3); }
        | expr '%' expr   { $$ = mk2("pv_mod", $1, $3); }
        | '-' expr %prec UMINUS { $$ = mk1("pv_neg", $2); }
        | expr EQ expr    { $$ = mk2("pv_eq", $1, $3); }
        | expr NE expr    { $$ = mk2("pv_ne", $1, $3); }
        | expr LT expr    { $$ = mk2("pv_lt", $1, $3); }
        | expr GT expr    { $$ = mk2("pv_gt", $1, $3); }
        | expr LE expr    { $$ = mk2("pv_le", $1, $3); }
        | expr GE expr    { $$ = mk2("pv_ge", $1, $3); }
        | NOT expr        { $$ = mk1("pv_not", $2); }
        | expr AND expr   { $$ = fmtstr("PV_AND(%s, %s)", $1, $3); free($1); free($3); }
        | expr OR expr    { $$ = fmtstr("PV_OR(%s, %s)",  $1, $3); free($1); free($3); }
        | primary         { $$ = $1; }
        ;

primary : NUMBER               { $$ = fmtstr("pv_num(%s)", $1); free($1); }
        | STRING               { $$ = fmtstr("pv_str(%s)", $1); free($1); }
        | BOOLLIT              { $$ = $1; }
        | '(' expr ')'         { $$ = $2; }
        | ASK '(' ')'          { $$ = strdup("pv_ask(pv_nil())"); }
        | ASK '(' expr ')'     { $$ = mk1("pv_ask", $3); }
        | IDENT '(' ')'        { $$ = emit_call($1, NULL); }
        | IDENT '(' args ')'   { $$ = emit_call($1, $3); }
        | IDENT                { $$ = $1; }
        ;

args    : expr                 { $$ = $1; }
        | args ',' expr        { $$ = fmtstr("%s, %s", $1, $3); free($1); free($3); }
        ;

%%

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <program.txt>\n", argv[0]);
        return 1;
    }
    yyin = fopen(argv[1], "r");
    if (!yyin) { perror(argv[1]); return 1; }

    if (yyparse() != 0) return 1;
    fclose(yyin);

    printf("/* Auto-generated by parsec2c from %s */\n", argv[1]);
    printf("#include \"parsec_runtime.h\"\n\n");
    printf("int main(void) {\n");
    for (int i = 0; i < declared_count; i++) {
        printf("    pv %s = pv_nil();\n", declared_vars[i]);
    }
    if (body_buf) fputs(body_buf, stdout);
    printf("    return 0;\n");
    printf("}\n");
    return 0;
}

void yyerror(const char *msg) {
    fprintf(stderr, "Parse error near line %d: %s\n", yylineno_, msg);
}
