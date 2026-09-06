// Every control-flow construct in TypeScript that can carry a decision,
// including the type-level syntax that must not be counted.

function ifElse(v: number): number {
    if (v > 0) {
        return 1;
    } else if (v < 0) {
        return -1;
    }
    return 0;
}

function forOf(items: number[]): number {
    let total = 0;
    for (const item of items) {
        total += item;
    }
    return total;
}

function whileLoop(n: number): number {
    while (n > 0) {
        n--;
    }
    return n;
}

function switchStatement(v: number): string {
    switch (v) {
        case 1:
            return "one";
        case 2:
            return "two";
        default:
            return "many";
    }
}

function tryCatch(text: string): unknown {
    try {
        return JSON.parse(text);
    } catch (e) {
        return null;
    }
}

function booleanOperators(a: boolean, b: boolean, c: boolean): boolean {
    return a && b || c;
}

function optionalParameter(name: string, title?: string): string {
    return title ?? name;
}

function ternary(v: number): number {
    return v > 0 ? 1 : 2;
}
