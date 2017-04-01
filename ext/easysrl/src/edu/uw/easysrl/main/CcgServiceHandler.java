package edu.uw.easysrl.main;

// Java packages
import java.io.*;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

import edu.uw.easysrl.semantics.lexicon.CompositeLexicon;
import edu.uw.easysrl.semantics.lexicon.Lexicon;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.grpc.stub.StreamObserver;
import com.google.protobuf.Empty;

import ai.marbles.grpc.LucidaServiceGrpc;
import ai.marbles.grpc.Request;
import ai.marbles.grpc.Response;
import ai.marbles.grpc.QueryInput;

import edu.uw.easysrl.syntax.grammar.Category;
import edu.uw.easysrl.syntax.parser.SRLParser;
import edu.uw.easysrl.syntax.parser.SRLParser.BackoffSRLParser;
import edu.uw.easysrl.syntax.parser.SRLParser.CCGandSRLparse;
import edu.uw.easysrl.syntax.parser.SRLParser.JointSRLParser;
import edu.uw.easysrl.syntax.parser.SRLParser.PipelineSRLParser;
import edu.uw.easysrl.syntax.tagger.POSTagger;
import edu.uw.easysrl.util.Util;


/**
 * Implementation of the easysrl ccg parser interface.
 */
public class CcgServiceHandler extends LucidaServiceGrpc.LucidaServiceImplBase {
	private static final Logger logger = LoggerFactory.getLogger(CcgServiceHandler.class);

	public class ConfigOptions implements EasySRL.CommandLineArguments {
		private String modelPath;

		ConfigOptions(String modelPath) { this.modelPath = modelPath; }

		public String getModel() { return modelPath; }

		public String getInputFile() { return ""; }

		// defaultValue = "tokenized", description = "(Optional) Input Format: one of \"tokenized\", \"POStagged\" (word|pos), or \"POSandNERtagged\" (word|pos|ner)")
		public String getInputFormat() { return "tokenized"; }

		public String getOutputFormat() { return "ccgbank"; }

		public String getParsingAlgorithm() { return "astar"; }

		// "(Optional) Maximum length of sentences in words. Defaults to 70.")
		public int getMaxLength() { return 70; }

		// "(Optional) Number of parses to return per sentence. Values >1 are only supported for A* parsing. Defaults to 1.")
		public int getNbest() { return 1; }

		// defaultValue = { "S[dcl]", "S[wq]", "S[q]", "S[b]\\NP", "NP" }, description = "(Optional) List of valid categories for the root node of the parse. Defaults to: S[dcl] S[wq] S[q] NP S[b]\\NP")
		public List<Category> getRootCategories() {
			ArrayList<Category> list = new ArrayList<>(5);
			list.add(Category.valueOf("S[dcl]"));
			list.add(Category.valueOf("S[wq]"));
			list.add(Category.valueOf("S[q]"));
			list.add(Category.valueOf("S[b]\\NP"));
			list.add(Category.valueOf("NP"));
			return list;
		}

		// defaultValue = "0.01", description = "(Optional) Prunes lexical categories whose probability is less than this ratio of the best category. Decreasing this value will slightly improve accuracy, and give more varied n-best output, but decrease speed. Defaults to 0.01 (currently only used for the joint model).")
		public double getSupertaggerbeam() { return 0.01; }

		// defaultValue = "1.0", description = "Use a specified supertagger weight, instead of the pretrained value.")
		public double getSupertaggerWeight() { return 1.0; }

		public boolean getHelp() { return true; }

		public boolean getDaemonize() { return true; }

		public int getPort() { return 8084; }
	}

	public interface Session {
		SRLParser getParser();
		InputReader getReader();
		ParsePrinter getPrinter();
		EasySRL.OutputFormat getOutputFormat();
		void lock();
		void unlock();
	}

	public class SynchronizedSession implements Session  {
		private SRLParser parser_;
		private InputReader reader_;
		private EasySRL.OutputFormat outputFormat_;
		private Lock inferLock_;

		public SRLParser getParser() { return parser_; }
		public InputReader getReader() { return reader_; }
		public ParsePrinter getPrinter() { return outputFormat_.printer; }
		public EasySRL.OutputFormat getOutputFormat() { return outputFormat_; }

		public void lock() {
			inferLock_.lock();
		}
		public void unlock() {
			inferLock_.unlock();
		}

		public SynchronizedSession(SRLParser parser, InputReader reader, EasySRL.OutputFormat outputFmt) {
			this.parser_ = parser;
			this.reader_  = reader;
			this.outputFormat_ = outputFmt;
			this.inferLock_ = new ReentrantLock();
		}
	}

	private HashMap<String, Session> sessionCache_ = new HashMap();
	private EasySRL.CommandLineArguments commandLineOptions_;
	private Session defaultSession_;

	/** Constructs the handler and initializes its EasySRL
	 * object.
	 */
	public CcgServiceHandler(String pathToModel) {
		commandLineOptions_ = new ConfigOptions(pathToModel);
	}

	public CcgServiceHandler(EasySRL.CommandLineArguments cmdLine) {
		commandLineOptions_ = cmdLine;
	}

	public void init() throws IOException, InterruptedException {
		// Lock in thread so calls to gRPC service are blocked until the default session is created.
		defaultSession_ = getSessionFromId("default", "CCGBANK");
	}

	private Session createSession(String oformat) throws IOException, InterruptedException {

		final EasySRL.InputFormat input = EasySRL.InputFormat.valueOf(commandLineOptions_.getInputFormat().toUpperCase());
		final File modelFolder = Util.getFile(EasySRL.absolutePath(commandLineOptions_.getModel()));

		if (!modelFolder.exists()) {
			logger.error("Couldn't load model from {}", commandLineOptions_.getModel());
			throw new InputMismatchException("Couldn't load model from from: " + commandLineOptions_.getModel());
		}

		final File pipelineFolder = new File(modelFolder, "/pipeline");
		logger.debug("Loading model from {} ...", commandLineOptions_.getModel());
		final EasySRL.OutputFormat outputFormat = EasySRL.OutputFormat.valueOf(oformat);
		ParsePrinter printer = outputFormat.printer;
		SRLParser parser2;

		if (pipelineFolder.exists()) {
			// Joint model
			final POSTagger posTagger = POSTagger.getStanfordTagger(new File(pipelineFolder, "posTagger"));
			final PipelineSRLParser pipeline = EasySRL.makePipelineParser(pipelineFolder, commandLineOptions_, 0.000001,
					printer.outputsDependencies());
			parser2 = new BackoffSRLParser(new JointSRLParser(EasySRL.getParserBuilder(commandLineOptions_).build(),
					posTagger), pipeline);
		} else {
			// Pipeline
			parser2 = EasySRL.makePipelineParser(modelFolder, commandLineOptions_, 0.000001, printer.outputsDependencies());
		}

		final SRLParser parser;
		if (printer.outputsLogic()) {
			// If we're outputing logic, load a lexicon
			final File lexiconFile = new File(modelFolder, "lexicon");
			final Lexicon lexicon = lexiconFile.exists() ? CompositeLexicon.makeDefault(lexiconFile)
					: CompositeLexicon.makeDefault();
			parser2 = new SRLParser.SemanticParser(parser2, lexicon);
		}

		InputReader reader;
		if (outputFormat == EasySRL.OutputFormat.EXTENDED || outputFormat == EasySRL.OutputFormat.PROLOG)
			reader = InputReader.make(EasySRL.InputFormat.valueOf("POSandNERtagged".toUpperCase()));
		else
			reader = InputReader.make(EasySRL.InputFormat.valueOf(commandLineOptions_.getInputFormat().toUpperCase()));

		/*
		if ((outputFormat == EasySRL.OutputFormat.PROLOG || outputFormat == EasySRL.OutputFormat.EXTENDED)
				&& input != EasySRL.InputFormat.POSANDNERTAGGED) {
			String msg = "Must use \"-i POSandNERtagged\" for this output";
			logger.error(msg);
			throw new Error(msg);
		}
		*/
		logger.debug("Model loaded: gRPC parser ready");

		return new SynchronizedSession(parser2, reader, outputFormat);
	}

	public static String parse(Session session, String sentence) {
		if (session.getParser() != null) {
			List<CCGandSRLparse> parses = session.getParser().parseTokens(session.getReader().readInput(sentence)
					.getInputWords());
			if (session.getOutputFormat() == EasySRL.OutputFormat.HTML)
				// id <= -1 means header and footer are not printed.
				return session.getPrinter().printJointParses(parses,0);
			else
				// id -1 disables printing id for CCGBANK
				return session.getPrinter().printJointParses(parses, -1);
		}
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
		logger.debug("Create({}}", request.getLUCID());

		if (request.getSpec().getContentList().isEmpty() ||
				request.getSpec().getContentList().get(0).getDataList().isEmpty()) {
			logger.info("empty content passed to service");
			throw new IllegalArgumentException();
		}

		try {
			responseObserver.onNext(Empty.newBuilder().build());
			QueryInput queryInput = request.getSpec().getContentList().get(0);
			getSessionFromId(request.getLUCID(), queryInput.getData(0).toString("UTF-8").toUpperCase());
			responseObserver.onCompleted();
		} catch (Exception e) {
			logger.error("Create({}) failed to create session - {}", request.getLUCID(), e.getMessage());
			//e.printStackTrace();
			responseObserver.onError(e);
		}

	}

	@Override
	/** {@inheritDoc} */
	public void learn(Request request, StreamObserver<Empty> responseObserver) {
		logger.debug("Learn({}}", request.getLUCID());

		responseObserver.onNext(Empty.newBuilder().build());
		responseObserver.onCompleted();
	}

	@Override
	/** {@inheritDoc} */
    public void infer(Request request, StreamObserver<Response> responseObserver) {
		logger.debug("Infer({}}", request.getLUCID());
		
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
            logger.info("exception caught - {}", e.getMessage());
            responseObserver.onError(e);
		} finally {
			if (session != null)
				session.unlock();
		}
	}
}
