// Every control-flow construct in ECMA-262 that can carry a decision.
// One function per construct.

function ifElse(v) {
    if (v > 0) {
        return 1;
    } else if (v < 0) {
        return -1;
    }
    return 0;
}

function forLoop(n) {
    let total = 0;
    for (let i = 0; i < n; i++) {
        total += i;
    }
    return total;
}

function forOf(items) {
    let total = 0;
    for (const item of items) {
        total += item;
    }
    return total;
}

function whileLoop(n) {
    while (n > 0) {
        n--;
    }
    return n;
}

function doWhileLoop(n) {
    do {
        n--;
    } while (n > 0);
    return n;
}

function switchStatement(v) {
    switch (v) {
        case 1:
            return "one";
        case 2:
            return "two";
        default:
            return "many";
    }
}

function tryCatch(text) {
    try {
        return JSON.parse(text);
    } catch (e) {
        return null;
    }
}

function booleanOperators(a, b, c) {
    return a && b || c;
}

function ternaryAndCoalesce(v) {
    const x = v > 0 ? 1 : 2;
    return v ?? x;
}

function optionalChaining(user) {
    return user?.profile?.theme;
}
