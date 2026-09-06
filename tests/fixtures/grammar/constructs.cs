// Every control-flow construct in the C# specification that can carry a
// decision. One method per construct.
namespace Grammar {
    public class Constructs {
        public int IfElse(int v) {
            if (v > 0) {
                return 1;
            } else if (v < 0) {
                return -1;
            }
            return 0;
        }

        public int ForLoop(int n) {
            int total = 0;
            for (int i = 0; i < n; i++) {
                total += i;
            }
            return total;
        }

        public int ForEach(int[] items) {
            int total = 0;
            foreach (int item in items) {
                total += item;
            }
            return total;
        }

        public int WhileLoop(int n) {
            while (n > 0) {
                n--;
            }
            return n;
        }

        public int DoWhileLoop(int n) {
            do {
                n--;
            } while (n > 0);
            return n;
        }

        public string SwitchStatement(int v) {
            switch (v) {
                case 1:
                    return "one";
                case 2:
                    return "two";
                default:
                    return "many";
            }
        }

        public int TryCatch(string text) {
            try {
                return int.Parse(text);
            } catch (System.FormatException) {
                return 0;
            }
        }

        public bool BooleanOperators(bool a, bool b, bool c) {
            return a && b || c;
        }

        public int TernaryAndCoalesce(int? v) {
            int x = v > 0 ? 1 : 2;
            return v ?? x;
        }
    }
}
