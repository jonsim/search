#include <stdio.h>
#include "util_number.h"

int main(int argc, char** argv)
{
    unsigned int input = 123456;
    unsigned int i;

    for (i = 0; i < 5; i++)
    {
        printf("%u rot %u = %u\n", input, i, rotate(input, i));
    }
    return 0;
}
