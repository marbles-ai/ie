package edu.uw.neuralccg.util.functional.map;

import java.util.HashMap;
import java.util.Optional;

public class OptionalHashMap<K, V> extends HashMap<K, V> {
	public Optional<V> getOptional(Object key) {
		return Optional.ofNullable(get(key));
	}
}
