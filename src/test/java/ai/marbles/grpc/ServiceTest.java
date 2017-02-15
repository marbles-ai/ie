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

//Java packages
import io.grpc.stub.StreamObserver;
import com.google.common.util.concurrent.ListenableFuture;

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
	}

	@Test
	public void testSyncClientSyncServer() {

		try {
			ServiceAcceptor server = new ServiceAcceptor(9001, new SyncHandler());
			server.start();

			ServiceConnector client = new ServiceConnector("localhost", 9001);
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
