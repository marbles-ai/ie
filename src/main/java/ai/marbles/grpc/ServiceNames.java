/*
 * Copyright (c) Marbles AI Corp. 2016-2017.
 * All rights reserved.
 * Author: Paul Glendenning
 */

package ai.marbles.grpc;

public final class ServiceNames {
	public static final String learnCommandName = "knowledge";
	public static final String createCommandName = "create";
	public static final String inferCommandName = "query";
	public static final String textTypeName = "text";
	public static final String urlTypeName = "url";
	public static final String imageTypeName = "image";
	public static final String unlearnTypeName = "unlearn";

    private ServiceNames() {
    }

    /**
     * Check validity of a type name.
     *
     * @param  typeName The type name to test.
     * @return True if typeName is avalid type.
     */
    public static boolean isTypeName(String typeName) {
        return typeName == imageTypeName || typeName == urlTypeName || typeName == textTypeName ||
            typeName == unlearnTypeName;
    }

    /**
     * Check validity of a command name.
     *
     * @param  cmdName  The command name to test.
     * @return True if cmdName is a valid command.
     */
    public static boolean isCommandName(String cmdName) {
        return cmdName == learnCommandName || cmdName == createCommandName ||
            cmdName == inferCommandName;
    }
}
