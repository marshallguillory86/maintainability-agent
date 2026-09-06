# C#

Methods, constructors, destructors, and the types — `class`,
`interface`, `struct`, `record`, `record struct` and `enum`. Types are
descended into, because that is where members live; a method body is
stepped over. Generic parameter lists are blanked before matching, so
`public List<T> Sort<T>(List<T> items) where T : IComparable` yields
`Sort`, and attributes are stripped with their arguments, so
`[Obsolete("x")]` is not read as a method called `Obsolete`.

Namespaces are handled in both forms: a braced `namespace Geo {` is
walked into without being graded, and C# 10's file-scoped `namespace
Geo;` declares nothing and is ignored rather than being allowed to
swallow the file.

**Properties are deliberately not declarations.** `public int Count {
get; set; }` has braces and would bound cleanly, and an ordinary C# tree
holds thousands of them — each one line long, each nobody's maintenance
burden. Counting them would dilute the population that every
declaration rate divides by. They are excluded by construction: a
property has no parameter list, and every pattern here requires one. The
same applies to a parameterless expression-bodied member
(`public int Area => w * h;`). A method written `public int Fast() =>
count_;` **is** counted — it has a parameter list.

Everything it misses, it misses in the safe direction:

- **Interface and abstract members** have no body, so they mint nothing.
  A positional `record Point(int X, int Y);` likewise.
- **Local functions** live inside a method body and are not counted.
- **Source-generated declarations** are not in the tree and are not seen.
- **Conditional compilation is not evaluated**, so a member in a
  disabled `#if` arm still counts.

