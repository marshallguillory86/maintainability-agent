// Every control-flow construct in the Java Language Specification that
// can carry a decision. One method per construct.
package grammar;

public class Constructs {
    public int ifElse(int v) {
        if (v > 0) {
            return 1;
        } else if (v < 0) {
            return -1;
        }
        return 0;
    }

    public int forLoop(int n) {
        int total = 0;
        for (int i = 0; i < n; i++) {
            total += i;
        }
        return total;
    }

    public int forEach(int[] items) {
        int total = 0;
        for (int item : items) {
            total += item;
        }
        return total;
    }

    public int whileLoop(int n) {
        while (n > 0) {
            n--;
        }
        return n;
    }

    public int doWhileLoop(int n) {
        do {
            n--;
        } while (n > 0);
        return n;
    }

    public String switchStatement(int v) {
        switch (v) {
            case 1:
                return "one";
            case 2:
                return "two";
            default:
                return "many";
        }
    }

    public int tryCatch(String text) {
        try {
            return Integer.parseInt(text);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public boolean booleanOperators(boolean a, boolean b, boolean c) {
        return a && b || c;
    }

    public int ternary(int v) {
        return v > 0 ? 1 : 2;
    }
}
