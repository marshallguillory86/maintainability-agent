package fixtures;

public class Annotated {

    @SuppressWarnings("unchecked")
    @Override
    public String toString() {
        return "annotated";
    }

    @Deprecated(since = "1.2")
    public int legacy() {
        return 0;
    }
}
