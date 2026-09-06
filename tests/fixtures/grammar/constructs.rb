# Every control-flow construct in the Ruby grammar that can carry a
# decision. One method per construct.

def if_elsif(v)
  if v > 0
    1
  elsif v < 0
    -1
  else
    0
  end
end

def modifier_if(v)
  return 0 if v.nil?
  v
end

def unless_statement(v)
  unless v.nil?
    return v
  end
  0
end

def while_loop(n)
  while n > 0
    n -= 1
  end
  n
end

def until_loop(n)
  until n <= 0
    n -= 1
  end
  n
end

def for_loop(items)
  total = 0
  for item in items
    total += item
  end
  total
end

def case_when(v)
  case v
  when 1 then "one"
  when 2 then "two"
  else "many"
  end
end

def begin_rescue(text)
  begin
    Integer(text)
  rescue ArgumentError
    0
  end
end

def boolean_operators(a, b, c)
  a && b || c
end

def word_operators(a, b)
  a and b
end

def ternary(v)
  v > 0 ? 1 : 2
end

def safe_navigation(v)
  v&.name
end
