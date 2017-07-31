package edu.uw.neuralccg;

// Java packages
import java.io.*;
import java.util.*;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

import com.typesafe.config.Config;
import edu.uw.easysrl.syntax.grammar.SyntaxTreeNode;
import edu.uw.easysrl.syntax.parser.Parser;
import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;

import io.grpc.stub.StreamObserver;
import com.google.protobuf.Empty;

import ai.marbles.grpc.LucidaServiceGrpc;
import ai.marbles.grpc.Request;
import ai.marbles.grpc.Response;
import ai.marbles.grpc.QueryInput;

import edu.uw.easysrl.util.Util;
import edu.uw.easysrl.main.EasySRL;
import edu.uw.easysrl.main.InputReader;
import edu.uw.easysrl.main.ParsePrinter;

import edu.uw.neuralccg.Main;


/**
 * Implementation of the easysrl ccg parser interface.
 */
public class CcgServiceHandler extends LucidaServiceGrpc.LucidaServiceImplBase {
	private static final Logger logger = LogManager.getLogger(CcgServiceHandler.class);

	public interface Session {
		Parser getParser();
		InputReader getReader();
		ParsePrinter getPrinter();
		EasySRL.OutputFormat getOutputFormat();
		void lock();
		void unlock();
	}

	public class SynchronizedSession implements Session  {
		private Parser parser_;
		private InputReader reader_;
		private EasySRL.OutputFormat outputFormat_;
		private Lock inferLock_;

		public Parser getParser() { return parser_; }
		public InputReader getReader() { return reader_; }
		public ParsePrinter getPrinter() { return outputFormat_.printer; }
		public EasySRL.OutputFormat getOutputFormat() { return outputFormat_; }

		public void lock() {
			inferLock_.lock();
		}
		public void unlock() {
			inferLock_.unlock();
		}

		public SynchronizedSession(Parser parser, InputReader reader, EasySRL.OutputFormat outputFmt) {
			this.parser_ = parser;
			this.reader_  = reader;
			this.outputFormat_ = outputFmt;
			this.inferLock_ = new ReentrantLock();
		}
	}

	private HashMap<String, Session> sessionCache_ = new HashMap();
	private Main.CommandLineArguments commandLineOptions_;
	private Config parameters_;
	private Session defaultSession_;

	public CcgServiceHandler(Main.CommandLineArguments cmdLine, Config params) {
        parameters_ = params;
	    commandLineOptions_ = cmdLine;
	}

	public void init() throws IOException, InterruptedException {
		// Lock in thread so calls to gRPC service are blocked until the default session is created.
		defaultSession_ = getSessionFromId("default", "CCGBANK");
	}

	private Session createSession(String oformat) throws IOException, InterruptedException {

		final EasySRL.InputFormat input = EasySRL.InputFormat.TOKENIZED;
		final File modelFolder = Util.getFile(EasySRL.absolutePath(commandLineOptions_.getModel()));

		if (!modelFolder.exists()) {
			logger.error("Couldn't load model from " + commandLineOptions_.getModel());
			throw new InputMismatchException("Couldn't load model from from: " + commandLineOptions_.getModel());
		}

        Parser parser = Main.initializeModel(parameters_, EasySRL.absolutePath(commandLineOptions_.getModel()));
		final EasySRL.OutputFormat outputFormat = EasySRL.OutputFormat.valueOf(oformat);
		ParsePrinter printer = outputFormat.printer;

		InputReader reader;
		if (outputFormat == EasySRL.OutputFormat.EXTENDED || outputFormat == EasySRL.OutputFormat.PROLOG)
			reader = InputReader.make(EasySRL.InputFormat.valueOf("POSandNERtagged".toUpperCase()));
		else
			reader = InputReader.make(EasySRL.InputFormat.TOKENIZED);

		logger.info("Model loaded: gRPC parser ready");

		return new SynchronizedSession(parser, reader, outputFormat);
	}

	/**
	 * Parse using default session
	 * @param sentence
	 * @return
	 */
	public String parse(String sentence) {
		return parse(defaultSession_, sentence);
	}

	public static String parse(Session session, String sentence) {
		if (session.getParser() != null) {
            final List<Util.Scored<SyntaxTreeNode>> scored_parses = session.getParser().doParsing(session.getReader().
                readInput(sentence));
            if (scored_parses != null) {
                List<SyntaxTreeNode> parses = scored_parses.stream()
                    .map(p -> p.getObject())
                    .collect(Collectors.toList());
                if (session.getOutputFormat() == EasySRL.OutputFormat.HTML)
                    // id <= -1 means header and footer are not printed.
                    return session.getPrinter().print(parses,0);
                else
                    // id -1 disables printing id for CCGBANK
                    return session.getPrinter().print(parses, -1);
            }

		}
		// TODO: notify failure
		return "";
	}

	synchronized private Session getSessionFromId(String sessionId, String outputFormat) throws IOException, InterruptedException {
		if (outputFormat != null && sessionId != null && !sessionId.isEmpty()) {
			Session session = sessionCache_.get(sessionId);
			if (session == null) {
				session = createSession(outputFormat);
				sessionCache_.put(sessionId, session);
			}
			return session;
		} else {
			return sessionCache_.getOrDefault(sessionId, defaultSession_);
		}
	}

	private Session getSessionFromId(String sessionId) throws IOException, InterruptedException {
		return getSessionFromId(sessionId, null);
	}

	@Override
	/** {@inheritDoc} */
	public void create(Request request, StreamObserver<Empty> responseObserver) {
		logger.debug(String.format("Create(%s)", request.getLUCID()));

		if (request.getSpec().getContentList().isEmpty() ||
				request.getSpec().getContentList().get(0).getDataList().isEmpty()) {
			logger.error("empty content - no session created");
			throw new IllegalArgumentException();
		}

		try {
			responseObserver.onNext(Empty.newBuilder().build());
			QueryInput queryInput = request.getSpec().getContentList().get(0);
			getSessionFromId(request.getLUCID(), queryInput.getData(0).toString("UTF-8").toUpperCase());
			responseObserver.onCompleted();
			logger.info("new session created - " + request.getLUCID());
		} catch (Exception e) {
			logger.error(String.format("Create(%s) failed to create session", request.getLUCID()), e);
			//e.printStackTrace();
			responseObserver.onError(e);
		}

	}

	@Override
	/** {@inheritDoc} */
	public void learn(Request request, StreamObserver<Empty> responseObserver) {
		logger.debug(String.format("Learn(%s)", request.getLUCID()));

		responseObserver.onNext(Empty.newBuilder().build());
		responseObserver.onCompleted();
	}

	@Override
	/** {@inheritDoc} */
    public void infer(Request request, StreamObserver<Response> responseObserver) {
		logger.debug(String.format("Infer(%s)", request.getLUCID()));

	    if (request.getSpec().getContentList().isEmpty() ||
                request.getSpec().getContentList().get(0).getDataList().isEmpty()) {
            logger.info("empty content passed to service");
	        throw new IllegalArgumentException();
	    }

	    Session session = null;
		try {
			QueryInput queryInput = request.getSpec().getContentList().get(0);
			session = getSessionFromId(request.getLUCID());
			session.lock();

			// FIXME: Response.msg should be an array
			// Only look for the first item in content and data.
			// The rest part of query is ignored.
			final StringBuilder output = new StringBuilder();
			for (int i = 0; i < queryInput.getDataList().size(); ++i) {
				String sentence = queryInput.getDataList().get(i).toString("UTF-8");
				output.append(parse(session, sentence));
				output.append("\n");
			}

			responseObserver.onNext(Response.newBuilder()
					.setMsg(output.toString())
					.build());
			responseObserver.onCompleted();

//        } catch (UnsupportedEncodingException e) {
//            logger.info("non UTF-8 encoding passed to service");
//            responseObserver.onError(e);
        } catch (Exception e) {
            logger.error("exception caught", e);
            responseObserver.onError(e);
		} finally {
			if (session != null)
				session.unlock();
		}
	}
}
