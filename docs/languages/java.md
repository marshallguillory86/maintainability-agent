# Java

Methods, constructors, and types — classes, interfaces, enums, records
and `@interface` declarations. Generic parameter lists are blanked
before matching, so `<T extends Comparable<T>>` neither ends a signature
early nor supplies the name; leading annotations are stripped with their
values, so `@Deprecated(since = "1.2")` is not read as a method called
`Deprecated`.

It walks member context only. A type's body is descended into, because
that is where its members live; a method's body is stepped over once its
end is known, so no statement inside it can be read as a declaration.
That single rule is why a nested class and its methods stay visible
while `doThing(x);` never becomes a declaration named `doThing`.

Everything it misses, it misses in the safe direction:

- **Declarations inside anonymous classes and lambdas** are not counted,
  because they sit inside a method body.
- **Text blocks** (`"""`) are not masked, so a brace inside one can
  desync depth. The indentation fallback bounds that to one declaration.
- **A field initialised with a method reference or an inline array** is
  not a declaration and is not reported as one.

Complexity for Java is the same keyword count used everywhere else here,
not a control-flow graph. Pair it with an external analyzer when the
number has to be exact.

