/*
 * Code take from Stack Overflow.
 * https://stackoverflow.com/questions/3833814/java-how-to-write-a-zip-function-what-should-be-the-return-type
 */
package ai.marbles.util;


import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;


public class Pair<T1, T2> implements Iterable<Object>, Cloneable{

    public static <X, Y> Pair<X, Y> makePair(X x, Y y){
        return new Pair<X, Y>(x, y);
    }

    public static <X> Pair<X, X[]> makePairFromArray(X... xs){
        if (xs.length == 0)
            return new Pair<X, X[]>(null, null);
        if (xs.length == 1)
            return new Pair<X, X[]>(xs[0], null);
        return new Pair<X, X[]>(xs[0], Arrays.copyOfRange(xs, 1, xs.length - 1));
    }

    public static <X, Y> Pair<X, Y> reverse(Pair<Y, X> original){
        return makePair(original.getSecond(), original.getFirst());
    }

    public static synchronized <X> void swap(Pair<X, X> swapped){
        X tmp = swapped.getFirst();
        swapped.setFirst(swapped.getSecond());
        swapped.setSecond(tmp);
    }

    @SuppressWarnings("unchecked")
    public static <X, Y> List<Object> asObjectList(Pair<X, Y> pair){
        return asList((Pair<Object, Object>) pair);
    }

    public static <X, Y> Object[] asObjectArray(Pair<X, Y> pair, Object[] array){
        return asObjectList(pair).toArray(array);
    }

    public static <X> List<X> asList(Pair<X, X> pair){
        ArrayList<X> list = new ArrayList<X>();
        list.add(pair.getFirst());
        list.add(pair.getSecond());
        return list;
    }

    public static <X> X[] asArray(Pair<X, X> pair, X[] array){
        return asList(pair).toArray(array);
    }

    public static <X> Iterator<X> typedIterator(Pair<X, X> pair){
        @SuppressWarnings("unchecked")
        final Iterator<X> it = (Iterator<X>) pair.iterator();
        return it;
    }

    public static <X> boolean isSymmetric(Pair<X, X> pair){
        return pair.equals(reverse(pair));
    }

    public static <X> boolean isReflexive(Pair<X, X> pair){
        X x1 = pair.getFirst();
        X x2 = pair.getSecond();

        if (x1 == null && x2 == null) return true;
        if (x1 == null && x2 != null) return false;
        if (x1 != null && x2 == null) return false;
        return x1.equals(x2);
    }

    public static <X, Y, Z> boolean isTransitive(Pair<X, Y> first, Pair<Y, Z> second){
        Y y1 = first.getSecond();
        Y y2 = second.getFirst();

        if (y1 == null && y2 == null) return true;
        if (y1 == null && y2 != null) return false;
        if (y1 != null && y2 == null) return false;
        return y1.equals(y2);
    }

    public static synchronized <X, Y> Pair<X, Y> immutablePair(Pair<X, Y> pair){
        final Pair<X, Y> wrapped = pair;
        return new Pair<X, Y>(null, null){

            @Override
            public X getFirst() {
                return wrapped.getFirst();
            }

            @Override
            public Y getSecond() {
                return wrapped.getSecond();
            }

            @Override
            public void setFirst(X first) {
                throw new UnsupportedOperationException();
            }

            @Override
            public void setSecond(Y second) {
                throw new UnsupportedOperationException();
            }

            @Override
            public int hashCode() {
                return wrapped.hashCode();
            }

            @Override
            public boolean equals(Object obj) {
                return wrapped.equals(obj);
            }

            @Override
            public String toString() {
                return wrapped.toString();
            }

            @Override
            public Iterator<Object> iterator() {
                return wrapped.iterator();
            }

            @Override
            public Object clone() throws CloneNotSupportedException {
                return wrapped.clone();
            }

            @Override
            public Pair<X, Y> copy() {
                return wrapped.copy();
            }

        };
    }

    public static synchronized <X, Y> Pair<X, Y> synchronizedPair(Pair<X, Y> pair){
        final Pair<X, Y> wrapped = pair;
        return new Pair<X, Y>(null, null){

            @Override
            public synchronized X getFirst() {
                return wrapped.getFirst();
            }

            @Override
            public synchronized void setFirst(X first) {
                wrapped.setFirst(first);
            }

            @Override
            public synchronized Y getSecond() {
                return wrapped.getSecond();
            }

            @Override
            public synchronized void setSecond(Y second) {
                wrapped.setSecond(second);
            }

            @Override
            public synchronized int hashCode() {
                return wrapped.hashCode();
            }

            @Override
            public synchronized boolean equals(Object obj) {
                return wrapped.equals(obj);
            }

            @Override
            public synchronized String toString() {
                return wrapped.toString();
            }

            @Override
            public synchronized Iterator<Object> iterator() {
                return wrapped.iterator();
            }

            @Override
            public synchronized Object clone() throws CloneNotSupportedException {
                return wrapped.clone();
            }

            @Override
            public synchronized Pair<X, Y> copy() {
                return wrapped.copy();
            }

        };
    }

    public Pair(T1 first, T2 second) {
        super();
        this.first = first;
        this.second = second;
    }

    public Pair(){
        super();
        this.first = null;
        this.second = null;
    }

    public Pair(Pair<T1, T2> copy) {
        first = copy.first;
        second = copy.second;
    }

    private T1 first;
    private T2 second;

    public T1 getFirst() {
        return first;
    }

    public void setFirst(T1 first) {
        this.first = first;
    }

    public T2 getSecond() {
        return second;
    }

    public void setSecond(T2 second) {
        this.second = second;
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((first == null) ? 0 : first.hashCode());
        result = prime * result + ((second == null) ? 0 : second.hashCode());
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        @SuppressWarnings("rawtypes")
        Pair other = (Pair) obj;
        if (first == null) {
            if (other.first != null)
                return false;
        } else if (!first.equals(other.first))
            return false;
        if (second == null) {
            if (other.second != null)
                return false;
        } else if (!second.equals(other.second))
            return false;
        return true;
    }

    @Override
    public String toString() {
        return "(" + first + ", " + second + ")";
    }

    @Override
    public Iterator<Object> iterator() {
        return new Iterator<Object>(){
            private int it = 0;

            @Override
            public boolean hasNext() {
                return it != 2;
            }

            @Override
            public Object next() {
                return (it++) == 0 ? first : second;
            }

            @Override
            public void remove() {
                throw new UnsupportedOperationException();
            }

        };
    }

    @Override
    public Object clone() throws CloneNotSupportedException {
        return super.clone();
    }

    public Pair<T1, T2> copy(){
        return makePair(first, second);
    }
}
