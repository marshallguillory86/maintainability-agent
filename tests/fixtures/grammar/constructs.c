/* Every control-flow construct in the C standard that can carry a
   decision. One function per construct. */

int if_else(int v) {
    if (v > 0) {
        return 1;
    } else if (v < 0) {
        return -1;
    }
    return 0;
}

int for_loop(int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += i;
    }
    return total;
}

int while_loop(int n) {
    while (n > 0) {
        n--;
    }
    return n;
}

int do_while_loop(int n) {
    do {
        n--;
    } while (n > 0);
    return n;
}

const char *switch_statement(int v) {
    switch (v) {
        case 1:
            return "one";
        case 2:
            return "two";
        default:
            return "many";
    }
}

int boolean_operators(int a, int b, int c) {
    return (a && b) || c;
}

int ternary(int v) {
    return v > 0 ? 1 : 2;
}

int goto_statement(int n) {
retry:
    if (n > 0) {
        n--;
        goto retry;
    }
    return n;
}
