package fixtures;

import java.util.List;
import java.util.Map;

public class Generics {

    public <T extends Comparable<T>> List<T> sorted(List<T> items) {
        items.sort(null);
        return items;
    }

    public Map<String, List<Integer>> index() {
        return null;
    }
}
