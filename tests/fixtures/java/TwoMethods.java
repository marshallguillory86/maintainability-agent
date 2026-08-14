package fixtures;

public class TwoMethods {

    public int first(int value) {
        if (value > 0) {
            return value;
        }
        return -value;
    }

    public String second() {
        return "ok";
    }
}
