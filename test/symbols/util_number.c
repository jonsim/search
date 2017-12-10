#include "util_number.h"
#include "math_add.h"
#include "math_mul.h"
#include <stdio.h>
unsigned int rotate(unsigned int x, unsigned int places)
{
    unsigned char i;
    unsigned char digits[10];
    unsigned int mask;
    unsigned int res;
    /* Partition */
    for (i = 9, mask = 1000000000; i <= 9; i--)
    {
        digits[i] = div(x, mask);
        x = mod(x, mask);
        mask = div(mask, 10);
    }
    /* Rebuild */
    for (i = 0, mask = 1, res = 0; i < 10; i++, mask = mul(mask, 10))
    {
        res = add(res, mul(mask, digits[mod(i + places, 10)]));
    }
    return res;
}
