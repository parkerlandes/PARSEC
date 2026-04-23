CC      = cc
CFLAGS  = -O2 -Wall

PARSEC2C = parsec2c
RUNTIME  = parsec_runtime.o

.PHONY: all clean

all: $(PARSEC2C) $(RUNTIME)

$(PARSEC2C): parsec.tab.c lex.yy.c
	$(CC) $(CFLAGS) -o $@ parsec.tab.c lex.yy.c

parsec.tab.c parsec.tab.h: parsec.y
	bison -d parsec.y

lex.yy.c: parsec.l parsec.tab.h
	flex parsec.l

$(RUNTIME): parsec_runtime.c parsec_runtime.h
	$(CC) $(CFLAGS) -c parsec_runtime.c

# Transpile + compile a single .txt program in one step.
# Usage:  make run PROG=../programs/helloworld.txt
run: all
	./$(PARSEC2C) $(PROG) > _out.c
	$(CC) $(CFLAGS) _out.c $(RUNTIME) -o _out
	./_out

clean:
	rm -f $(PARSEC2C) $(RUNTIME) parsec.tab.c parsec.tab.h lex.yy.c _out _out.c
