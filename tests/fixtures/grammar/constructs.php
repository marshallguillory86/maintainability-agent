<?php
// Every control-flow construct in the PHP language reference that can
// carry a decision. One function per construct.

function ifElseif(int $v): int {
    if ($v > 0) {
        return 1;
    } elseif ($v < 0) {
        return -1;
    }
    return 0;
}

function forLoop(int $n): int {
    $total = 0;
    for ($i = 0; $i < $n; $i++) {
        $total += $i;
    }
    return $total;
}

function foreachLoop(array $items): int {
    $total = 0;
    foreach ($items as $item) {
        $total += $item;
    }
    return $total;
}

function whileLoop(int $n): int {
    while ($n > 0) {
        $n--;
    }
    return $n;
}

function doWhileLoop(int $n): int {
    do {
        $n--;
    } while ($n > 0);
    return $n;
}

function switchStatement(int $v): string {
    switch ($v) {
        case 1:
            return "one";
        case 2:
            return "two";
        default:
            return "many";
    }
}

function matchExpression(int $v): string {
    return match($v) {
        1 => "one",
        2 => "two",
        default => "many",
    };
}

function tryCatch(string $text): int {
    try {
        return (int) $text;
    } catch (TypeError $e) {
        return 0;
    }
}

function booleanOperators(bool $a, bool $b, bool $c): bool {
    return $a && $b || $c;
}

function wordOperators(bool $a, bool $b): bool {
    return $a and $b;
}

function ternaryAndCoalesce(?int $v): int {
    $x = $v > 0 ? 1 : 2;
    return $v ?? $x;
}

function elvisOperator($v) {
    return $v ?: 0;
}
