package grammar

// Every control-flow construct in the Go specification's Statements
// section that can carry a decision. One function per construct so a
// disagreement names the construct rather than a file.

func ifElse(v int) int {
	if v > 0 {
		return 1
	} else if v < 0 {
		return -1
	}
	return 0
}

func forThreeClause(n int) int {
	total := 0
	for i := 0; i < n; i++ {
		total += i
	}
	return total
}

func forRange(items []int) int {
	total := 0
	for _, item := range items {
		total += item
	}
	return total
}

func forCondition(n int) int {
	for n > 0 {
		n--
	}
	return n
}

func expressionSwitch(v int) string {
	switch v {
	case 1:
		return "one"
	case 2:
		return "two"
	default:
		return "many"
	}
}

func typeSwitch(v interface{}) string {
	switch v.(type) {
	case int:
		return "int"
	case string:
		return "string"
	}
	return "other"
}

func selectStatement(a chan int, b chan int) int {
	select {
	case x := <-a:
		return x
	case y := <-b:
		return y
	}
}

func booleanOperators(a bool, b bool, c bool) bool {
	return a && b || c
}

func gotoStatement(n int) int {
retry:
	if n > 0 {
		n--
		goto retry
	}
	return n
}

func (b *box[T]) genericMethod(v T) T {
	if b.empty {
		return v
	}
	return b.item
}
