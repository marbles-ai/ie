/*
 * Copyright (c) Marbles AI Corp. 2016-2017.
 * All rights reserved.
 * Author: Paul Glendenning
 */

package ai.marbles.grpc;

//Java packages
import com.google.protobuf.Empty;
import io.grpc.stub.StreamObserver;
import com.google.common.util.concurrent.ListenableFuture;
import ai.marbles.grpc.ServiceAcceptor;
import ai.marbles.grpc.ServiceConnector;
import ai.marbles.grpc.ServiceNames;

import static org.junit.Assert.*;
import org.junit.Test;

public class ServiceTest {
	public class SyncHandler extends LucidaServiceGrpc.LucidaServiceImplBase  {
		@Override
		public void infer(Request request, StreamObserver<Response> responseObserver) {
			Response reply = Response.newBuilder().setMsg("got infer").build();
			responseObserver.onNext(reply);
			responseObserver.onCompleted();
		}
		@Override
		public void create(Request request, StreamObserver<Empty> responseObserver) {
			responseObserver.onNext(Empty.newBuilder().build());
			responseObserver.onCompleted();
		}

	}

	@Test
	public void testSyncClientSyncServer() {

		try {
			ServiceAcceptor server = new ServiceAcceptor(9001, new SyncHandler());
			server.start();

			ServiceConnector client = new ServiceConnector("localhost", 9001);
			client.create("1");
			Request req = Request.newBuilder().build();
			String resp = client.infer(req);
			assertTrue(resp.equals("got infer"));

			assertTrue(client.shutdown().blockUntilShutdown(3000));
			assertTrue(server.shutdown().blockUntilShutdown(3000));
		} catch(Exception e) {
			fail(e.getMessage());
		}
	}

	@Test
	public void testAsyncClientSyncServer() {
		try {
			ServiceAcceptor server = new ServiceAcceptor(9002, new SyncHandler());
			server.start();

			ServiceConnector client = new ServiceConnector("localhost", 9002);
			client.create("1");
			Request req = Request.newBuilder().build();

			ListenableFuture<Response> rpc = client.getFutureStub().infer(req);

			Response resp = rpc.get();
			assertTrue(resp != null);
			assertTrue(resp.getMsg().equals("got infer"));

			assertTrue(client.shutdown().blockUntilShutdown(3000));
			assertTrue(server.shutdown().blockUntilShutdown(3000));
		} catch(Exception e) {
			fail(e.getMessage());
		}
	}
}
