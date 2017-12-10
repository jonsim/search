#include "math_mul.h"
#include "math_add.h"

unsigned int mul(unsigned int x, unsigned int y)
{
    int i, acc;
    for (i = 0, acc = 0; i < y; i++, acc = add(acc, x));
    return acc;
}

unsigned int div(unsigned int x, unsigned int y)
{
    return x / y;
}

unsigned int mod(unsigned int x, unsigned int y)
{
    return x % y;
}
