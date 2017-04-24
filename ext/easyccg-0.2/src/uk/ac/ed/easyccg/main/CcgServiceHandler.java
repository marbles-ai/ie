package uk.ac.ed.easyccg.main;

// Java packages
import java.io.*;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

import io.grpc.stub.StreamObserver;
import com.google.protobuf.Empty;

import ai.marbles.grpc.LucidaServiceGrpc;
import ai.marbles.grpc.Request;
import ai.marbles.grpc.Response;
import ai.marbles.grpc.QueryInput;



/**
 * Test interface.
 */
public class CcgServiceHandler extends LucidaServiceGrpc.LucidaServiceImplBase {

    public CcgServiceHandler(String pathToModel) {
    }

    public void init() {
    }

    public String parse(String sentence) {
        return "";
    }

    @Override
    /** {@inheritDoc} */
    public void create(Request request, StreamObserver<Empty> responseObserver) {
        responseObserver.onNext(Empty.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    /** {@inheritDoc} */
    public void learn(Request request, StreamObserver<Empty> responseObserver) {
        responseObserver.onNext(Empty.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    /** {@inheritDoc} */
    public void infer(Request request, StreamObserver<Response> responseObserver) {
        responseObserver.onNext(Response.newBuilder().build());
        responseObserver.onCompleted();
    }
}