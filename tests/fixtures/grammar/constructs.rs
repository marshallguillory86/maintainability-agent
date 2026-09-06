// Every control-flow construct in the Rust reference that can carry a
// decision. One function per construct.

pub fn if_else(v: i32) -> i32 {
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

pub fn if_let(v: Option<i32>) -> i32 {
    if let Some(x) = v {
        return x;
    }
    0
}

pub fn while_loop(mut n: i32) -> i32 {
    while n > 0 {
        n -= 1;
    }
    n
}

pub fn while_let(mut items: Vec<i32>) -> i32 {
    let mut total = 0;
    while let Some(x) = items.pop() {
        total += x;
    }
    total
}

pub fn for_loop(items: &[i32]) -> i32 {
    let mut total = 0;
    for item in items {
        total += item;
    }
    total
}

pub fn loop_forever(mut n: i32) -> i32 {
    loop {
        n -= 1;
        if n < 0 {
            break;
        }
    }
    n
}

pub fn match_arms(v: i32) -> &'static str {
    match v {
        1 => "one",
        2 => "two",
        _ => "many",
    }
}

pub fn boolean_operators(a: bool, b: bool, c: bool) -> bool {
    a && b || c
}

pub fn question_mark(text: &str) -> Result<i32, std::num::ParseIntError> {
    let value = text.parse::<i32>()?;
    Ok(value + 1)
}
