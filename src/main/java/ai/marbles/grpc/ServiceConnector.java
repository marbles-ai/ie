/*
 * Copyright 2016 (c). All rights reserved.
 * Author: Paul Glendenning
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 *
 *    * Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 *    * Redistributions in binary form must reproduce the above
 * copyright notice, this list of conditions and the following disclaimer
 * in the documentation and/or other materials provided with the
 * distribution.
 *
 *    * Neither the name of the author, nor the names of other
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

package ai.marbles.grpc;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.Channel;
/* import io.grpc.Status; */
import io.grpc.StatusRuntimeException;
import com.google.protobuf.ByteString;

import java.io.UnsupportedEncodingException;
import java.net.UnknownServiceException;
import java.util.Collections;
import java.math.BigInteger;
import java.security.SecureRandom;
import static java.util.concurrent.TimeUnit.MILLISECONDS;
import static java.util.concurrent.TimeUnit.DAYS;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lucida client of gRPC service.
 */
public final class ServiceConnector {
	private static final Logger logger = LoggerFactory.getLogger(ServiceConnector.class);

	private final ManagedChannel channel_;
	private final LucidaServiceGrpc.LucidaServiceBlockingStub blockingStub_;
	private final LucidaServiceGrpc.LucidaServiceStub asyncStub_;
	private final LucidaServiceGrpc.LucidaServiceFutureStub futureStub_;
	private final SecureRandom random_ = new SecureRandom();

	/**
	 * Construct client for accessing a Lucida service at {@code host:port}.
	 * If port=443 then the channel will be secure via TLS, otherwise the channel
	 * is insecure. No authentication is provided in either case.
	 *
	 * @param host  Fully qualified host name
	 * @param port  The port number [1,65536)
	 */
	public ServiceConnector(String host, int port) {
		this(ManagedChannelBuilder.forAddress(host, port).usePlaintext(true));
	}

	/**
	 * Construct client for accessing a Lucida service using an existing channel.
	 * The channel credentials and encryption is dictated by the channelBuilder.
	 *
	 * @param channelBuilder The channel builder.
	 * @see io.grpc.ManagedChannelBuilder
	 */
	public ServiceConnector(ManagedChannelBuilder<?> channelBuilder) {
		channel_ = channelBuilder.build();
		blockingStub_ = LucidaServiceGrpc.newBlockingStub(channel_);
		asyncStub_ = LucidaServiceGrpc.newStub(channel_);
		futureStub_ = LucidaServiceGrpc.newFutureStub(channel_);
	}

	/**
	 * Channel accessor.
	 *
	 * @return The io.grpc.Channel for this client.
	 */
	public Channel getChannel() {
		return channel_;
	}

	/**
	 * Stub accessor.
	 *
	 * @return The blocking stub for this client.
	 */
	public LucidaServiceGrpc.LucidaServiceBlockingStub getBlockingStub() {
		return blockingStub_;
	}

	/**
	 * Stub accessor.
	 *
	 * @return The async stub for this client.
	 */
	public LucidaServiceGrpc.LucidaServiceStub getAsyncStub() {
		return asyncStub_;
	}

	/**
	 * Stub accessor.
	 *
	 * @return The future stub for this client.
	 */
	public LucidaServiceGrpc.LucidaServiceFutureStub getFutureStub() {
		return futureStub_;
	}

	/**
	 * Shutdown the client connection gracefully.
	 */
	public ServiceConnector shutdown() {
		if (channel_ != null) {
			channel_.shutdown();
		}
		return this;
	}

	/**
	 * Shutdown the client connection.
	 *
	 * @param   force   Force an immediate shutdown.
	 */
	public ServiceConnector shutdown(boolean force) {
		if (channel_ != null) {
			if (force)
				channel_.shutdownNow();
			else
				channel_.shutdown();
		}
		return this;
	}

	/**
	 * Await termination on the main thread since the grpc library uses daemon threads.
	 */
	public void blockUntilShutdown() throws InterruptedException {
		if (channel_ != null) {
			while (channel_.awaitTermination(365, DAYS)) {
				/* do nothing */
			}
		}
	}

	/**
	 * Await termination on the main thread since the grpc library uses daemon threads.
	 *
	 * @param timeout   Timeout in milliseconds.
	 * @return          True if shutdown completed. False on timeout.
	 */
	public boolean blockUntilShutdown(long timeout) throws InterruptedException {
		if (channel_ != null) {
			return channel_.awaitTermination(timeout, MILLISECONDS);
		}
		return true;
	}

	/**
	 * Create a random string.
	 *
	 * @return  A nonce.
	 */
	public String createNonce() {
		String n = new BigInteger(130, random_).toString(32);
		return n;
	}

	/**
	 * Build a generic request for learn, infer, create.
	 * @param id    The LUCID.
	 * @param spec  The query spec.
	 * @return The request.
	 */
	public static Request buildRequest(String id, QuerySpec spec) {
		return Request.newBuilder().setLUCID(id).setSpec(spec).build();
	}

	/**
	 * Create an intelligent instance based on supplied id. This is a
	 * blocking call.
	 *
	 * @param  id   The LUCID.
	 */
	public void create(String id) throws UnknownServiceException {
		logger.info("{} {}", ServiceNames.createCommandName, id);
		Request request = Request.newBuilder()
				.setLUCID(id)
				.setSpec(QuerySpec.newBuilder()
					.setName(ServiceNames.createCommandName))
				.build();
		try {
			blockingStub_.create(request);
		} catch (StatusRuntimeException e) {
			logger.warn("RPC failed: {}", e.getMessage());
			throw new UnknownServiceException(e.getMessage());
		}
	}

	/**
	 * General blocking request for learn. Building is left to the caller.
	 * @param  request  The request.
	 */
	public void learn(Request request) throws UnknownServiceException {
		try {
			blockingStub_.learn(request);
		} catch (StatusRuntimeException e) {
			logger.warn("RPC failed: {}", e.getMessage());
			throw new UnknownServiceException(e.getMessage());
		}
	}

	/**
	 * Build a request for learn. Content can be text, url, or image data.
	 *
	 * @param id        The LUCID.
	 * @param content   The data to learn from.
	 * @return The request.
	 */
	public static Request buildLearnRequest(String id, java.lang.Iterable<QueryInput> content) {
		logger.info("BLD.Learn {} variant {}", ServiceNames.learnCommandName, id);
		return Request.newBuilder()
			.setLUCID(id)
			.setSpec(QuerySpec.newBuilder()
				.setName(ServiceNames.learnCommandName)
				.addAllContent(content))
			.build();
	}

	/**
	 * Build a request for learn. Content can be text, url, or image data.
	 *
	 * @param id        The LUCID.
	 * @param content   The data to learn from.
	 * @return The request.
	 */
	public static Request buildLearnRequest(String id, QueryInput content) {
		return buildLearnRequest(id, Collections.singletonList(content));
	}

	/**
	 * General blocking request for infer. Building is left to the caller.
	 * @param  request  The request.
	 * @return A String if successful, else null.
	 */
	public String infer(Request request) throws UnknownServiceException {
		Response result;
		try {
			result = blockingStub_.infer(request);
		} catch (StatusRuntimeException e) {
			logger.warn("RPC failed: {}", e.getMessage());
			throw new UnknownServiceException(e.getMessage());
		}
		return result.getMsg();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @param data  The data to infer from.
	 * @param tags  Tags to attach to request.
	 * @return The request.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, ByteString data, java.lang.Iterable<String> tags) {
		logger.info("BLD.Infer {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
			.setLUCID(id)
			.setSpec(QuerySpec.newBuilder()
				.setName(ServiceNames.inferCommandName)
				.addContent(QueryInput.newBuilder()
					.setType(type)
					.addData(data)
					.addAllTags(tags)))
			.build();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @param data  The data to infer from.
	 * @param tags  Tags to attach to request.
	 * @return The request.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, String data, java.lang.Iterable<String> tags) throws UnsupportedEncodingException {
		logger.info("BLD.Infer {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
				.setLUCID(id)
				.setSpec(QuerySpec.newBuilder()
						.setName(ServiceNames.inferCommandName)
						.addContent(QueryInput.newBuilder()
								.setType(type)
								.addData(ByteString.copyFrom(data, "UTF-8"))
								.addAllTags(tags)))
				.build();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @param data  The data to iner from.
	 * @return A request object.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, ByteString data) {
		logger.info("SYNC  {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
			.setLUCID(id)
			.setSpec(QuerySpec.newBuilder()
				.setName(ServiceNames.inferCommandName)
				.addContent(QueryInput.newBuilder()
					.setType(type)
					.addData(data)))
			.build();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @param data  The data to infer from.
	 * @return A request object.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, String data) throws UnsupportedEncodingException {
		logger.info("SYNC  {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
				.setLUCID(id)
				.setSpec(QuerySpec.newBuilder()
						.setName(ServiceNames.inferCommandName)
						.addContent(QueryInput.newBuilder()
								.setType(type)
								.addData(ByteString.copyFrom(data,"UTF-8"))))
				.build();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @param data  The data to infer from.
	 * @param tag   A Tag to attach to request.
	 * @return A request object.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, ByteString data, String tag) {
		logger.info("SYNC  {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
			.setLUCID(id)
			.setSpec(QuerySpec.newBuilder()
				.setName(ServiceNames.inferCommandName)
				.addContent(QueryInput.newBuilder()
					.setType(type)
					.addData(data)
					.addTags(tag)))
			.build();
	}

	/**
	 * Build a request for infer from text or url or bytes.
	 *
	 * @param id    The LUCID.
	 * @param type  A service name type.
	 * @return      A request object.
	 * @see ServiceNames
	 */
	public static Request buildInferRequest(String id, String type, String data, String tag) throws UnsupportedEncodingException {
		logger.info("SYNC  {} {} {}", ServiceNames.inferCommandName, type, id);
		if (!ServiceNames.isTypeName(type))
			return null;
		return Request.newBuilder()
				.setLUCID(id)
				.setSpec(QuerySpec.newBuilder()
						.setName(ServiceNames.inferCommandName)
						.addContent(QueryInput.newBuilder()
								.setType(type)
								.addData(ByteString.copyFrom(data,"UTF-8"))
								.addTags(tag)))
				.build();
	}
}
