/*
 * Copyright (c) Marbles AI Corp. 2016-2017.
 * All rights reserved.
 * Author: Paul Glendenning
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
