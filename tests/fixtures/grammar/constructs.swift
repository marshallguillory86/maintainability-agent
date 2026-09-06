// Every control-flow construct in the Swift language guide that can
// carry a decision. One function per construct.

func ifElse(_ v: Int) -> Int {
    if v > 0 {
        return 1
    } else if v < 0 {
        return -1
    }
    return 0
}

func guardStatement(_ v: Int?) -> Int {
    guard let value = v else {
        return 0
    }
    return value
}

func forLoop(_ items: [Int]) -> Int {
    var total = 0
    for item in items {
        total += item
    }
    return total
}

func whileLoop(_ n: Int) -> Int {
    var count = n
    while count > 0 {
        count -= 1
    }
    return count
}

func repeatWhile(_ n: Int) -> Int {
    var count = n
    repeat {
        count -= 1
    } while count > 0
    return count
}

func switchStatement(_ v: Int) -> String {
    switch v {
    case 1:
        return "one"
    case 2:
        return "two"
    default:
        return "many"
    }
}

func booleanOperators(_ a: Bool, _ b: Bool, _ c: Bool) -> Bool {
    return a && b || c
}

func ternaryAndCoalesce(_ v: Int?) -> Int {
    let x = (v ?? 0) > 0 ? 1 : 2
    return x
}
