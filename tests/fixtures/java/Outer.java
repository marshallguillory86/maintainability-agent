package fixtures;

public class Outer {

    public int outerMethod() {
        return 1;
    }

    static final class Inner {

        public int innerMethod() {
            return 2;
        }
    }
}
