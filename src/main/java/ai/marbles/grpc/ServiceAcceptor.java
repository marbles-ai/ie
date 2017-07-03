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

import io.grpc.Server;
import io.grpc.ServerBuilder;

import java.io.IOException;
import static java.util.concurrent.TimeUnit.MILLISECONDS;

import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;

/**
 * A gRPC server for the LucidaService service.
 */
public class ServiceAcceptor {
	private static final Logger logger = LogManager.getLogger(ServiceAcceptor.class);

	private final int port_;
	private final Server server_;

	/** 
	  * Create a server listening on {@code port} using service to handle requests.
	  *
	  * @param  port    The port to listen on
	  * @param  service The service used to handle requests.
	  */
	public ServiceAcceptor(int port, LucidaServiceGrpc.LucidaServiceImplBase service) throws IOException {
		this(ServerBuilder.forPort(port), port, service);
	}

	/**
	 * Create a server using serverBuilder as a base and using service to handle requests.
	 */
	public ServiceAcceptor(ServerBuilder<?> serverBuilder, int port, LucidaServiceGrpc.LucidaServiceImplBase service) {
		this.port_ = port;
		server_ = serverBuilder.addService(service)
				.build();
	}

	/**
	 * Server accessor.
	 *
	 * @return The server.
	 */
	public Server getServer() {
		return server_;
	}

	/** 
	 * Start serving requests. Requests are handled in daemon threads.
	 */
	public void start() throws IOException {
		server_.start();
		logger.info("Server started, listening on " + port_);
		Runtime.getRuntime().addShutdownHook(new Thread() {
			@Override
			public void run() {
				// Use stderr here since the logger may have been reset by its JVM shutdown hook.
				System.err.println("*** shutting down gRPC server since JVM is shutting down");
				ServiceAcceptor.this.shutdown();
				System.err.println("*** server shut down");
			}
		});
	}

	/** 
	 * Stop serving requests and shutdown resources.
	 */
	public ServiceAcceptor shutdown() {
		if (server_ != null) {
			server_.shutdown();
		}
		return this;
	}

	/**
	 * Stop serving requests and shutdown resources.
	 *
	 * @param   force   Force an immediate shutdown.
	 */
	public ServiceAcceptor shutdown(boolean force) {
		if (server_ != null) {
			if (force)
				server_.shutdownNow();
			else
				server_.shutdown();
		}
		return this;
	}

	/**
	 * Await termination on the main thread since the grpc library uses daemon threads.
	 */
	public void blockUntilShutdown() throws InterruptedException {
		if (server_ != null) {
			server_.awaitTermination();
		}
	}

	/**
	 * Await termination on the main thread since the grpc library uses daemon threads.
	 *
	 * @param timeout   Timeout in milliseconds.
	 * @return          True if shutdown completed. False on timeout.
	 */
	public boolean blockUntilShutdown(long timeout) throws InterruptedException {
		if (server_ != null) {
			return server_.awaitTermination(timeout, MILLISECONDS);
		}
		return true;
	}
}
