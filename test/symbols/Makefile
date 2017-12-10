.PHONY: all clean

# Build setup
CC = gcc
AR = ar
C_FLAGS = -Wall -pedantic -O0 -g
L_FLAGS = -Wall -pedantic -O0 -g

# PHONY targets
all: libmath.a libnumber.a decimals

clean:
	rm -f decimals *.o *.a *.so

# Object targets
%.o: %.c
	$(CC) $(C_FLAGS) -c -o $@ $<

# Library targets
libmath.a: math_add.o math_mul.o
	$(AR) rcs -o $@ $^

libnumber.a: util_number.o
	$(AR) rcs -o $@ $^

# Binary targets
decimals: decimals.o libnumber.a libmath.a
	$(CC) $(L_FLAGS) -o $@ $< -L. -lnumber