%option noyywrap nounput noinput
%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "parsec.tab.h"

int yylineno_ = 1;
%}

%%

"//"[^\n]*          /* line comment */
[ \t\r]+            /* whitespace */
\n                  { yylineno_++; }

"let"               { return LET; }
"print"             { return PRINT; }
"ask"               { return ASK; }
"if"                { return IF; }
"else"              { return ELSE; }
"loop"              { return LOOP; }
"while"             { return WHILE; }
"and"               { return AND; }
"or"                { return OR; }
"not"               { return NOT; }
"true"              { yylval.sval = strdup("pv_bool(true)");  return BOOLLIT; }
"false"             { yylval.sval = strdup("pv_bool(false)"); return BOOLLIT; }

[0-9]+\.[0-9]+      { yylval.sval = strdup(yytext); return NUMBER; }
[0-9]+              { yylval.sval = strdup(yytext); return NUMBER; }

\"([^"\\\n]|\\.)*\" { yylval.sval = strdup(yytext); return STRING; }

[a-zA-Z_][a-zA-Z0-9_]* { yylval.sval = strdup(yytext); return IDENT; }

"=="                { return EQ; }
"!="                { return NE; }
"<="                { return LE; }
">="                { return GE; }
"<"                 { return LT; }
">"                 { return GT; }

"+"|"-"|"*"|"/"|"%"|"="|"("|")"|"{"|"}"|","  { return yytext[0]; }

.                   { fprintf(stderr, "Unexpected character '%s' on line %d\n", yytext, yylineno_); exit(1); }

%%
