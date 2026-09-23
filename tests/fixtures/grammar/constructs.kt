// Every control-flow construct in the Kotlin language specification that
// can carry a decision. One function per construct.

fun ifElse(v: Int): Int {
    if (v > 0) {
        return 1
    } else if (v < 0) {
        return -1
    }
    return 0
}

fun forLoop(items: List<Int>): Int {
    var total = 0
    for (item in items) {
        total += item
    }
    return total
}

fun whileLoop(n: Int): Int {
    var count = n
    while (count > 0) {
        count -= 1
    }
    return count
}

fun doWhile(n: Int): Int {
    var count = n
    do {
        count -= 1
    } while (count > 0)
    return count
}

fun whenStatement(v: Int): String {
    var out = "none"
    when (v) {
        1 -> out = "one"
        2 -> out = "two"
    }
    return out
}

fun whenWithElse(v: Int): String {
    when (v) {
        1 -> return "one"
        2 -> return "two"
        else -> return "many"
    }
}

fun whenWithoutSubject(a: Int, b: Int): String {
    when {
        a > b -> return "a"
        a < b -> return "b"
        else -> return "equal"
    }
}

fun booleanOperators(a: Boolean, b: Boolean, c: Boolean): Boolean {
    return a && b || c
}

fun elvisOperator(name: String?): String {
    return name ?: "anonymous"
}

fun safeCall(user: User?): String? {
    return user?.address?.city
}

fun nullableTypes(id: Int?, tag: String?): String {
    return "$id$tag"
}

fun lambdaAndFunctionType(items: List<Int>, transform: (Int) -> Int): Int {
    var total = 0
    items.forEach { item -> total += transform(item) }
    return total
}

fun tryCatch(v: Int): Int {
    try {
        return risky(v)
    } catch (e: IllegalStateException) {
        return 0
    }
}
