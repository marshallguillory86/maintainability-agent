// Every control-flow construct in the C++ standard that can carry a
// decision, plus the ones C does not have. One function per construct.
#include <vector>

int if_else(int v) {
    if (v > 0) {
        return 1;
    } else if (v < 0) {
        return -1;
    }
    return 0;
}

int range_for(const std::vector<int> &items) {
    int total = 0;
    for (int item : items) {
        total += item;
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

int try_catch(int v) {
    try {
        return 100 / v;
    } catch (...) {
        return 0;
    }
}

int boolean_operators(int a, int b, int c) {
    return (a && b) || c;
}

int ternary(int v) {
    return v > 0 ? 1 : 2;
}
