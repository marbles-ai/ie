package edu.uw.easysrl.main;

// Java packages
import java.io.*;
import java.util.*;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

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

	/**
	 * Since EasySRL is not thread-safe, we enforce the use to be single-threaded.
	 */
	private Lock infer_lock;

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

	private EasySRL.CommandLineArguments commandLineOptions;
	private SRLParser parser;
	private InputReader reader;
	private ParsePrinter printer;

	/** Constructs the handler and initializes its EasySRL
	 * object.
	 */
	public CcgServiceHandler(String pathToModel) {
		commandLineOptions = new ConfigOptions(pathToModel);
		infer_lock = new ReentrantLock();
	}

	public CcgServiceHandler(EasySRL.CommandLineArguments cmdLine) {
		commandLineOptions = cmdLine;
		infer_lock = new ReentrantLock();
	}

	public void init() throws IOException, InterruptedException {

		final EasySRL.InputFormat input = EasySRL.InputFormat.valueOf(commandLineOptions.getInputFormat().toUpperCase());
		final File modelFolder = Util.getFile(commandLineOptions.getModel());

		if (!modelFolder.exists()) {
			logger.error("Couldn't load model from {}", commandLineOptions.getModel());
			throw new InputMismatchException("Couldn't load model from from: " + commandLineOptions.getModel());
		}

		final File pipelineFolder = new File(modelFolder, "/pipeline");
		logger.debug("Loading model from {} ...", commandLineOptions.getModel());
		final EasySRL.OutputFormat outputFormat = EasySRL.OutputFormat.valueOf("CCGBANK");
		this.printer = outputFormat.printer;

		SRLParser parser2;
		if (pipelineFolder.exists()) {
			// Joint model
			final POSTagger posTagger = POSTagger.getStanfordTagger(new File(pipelineFolder, "posTagger"));
			final PipelineSRLParser pipeline = EasySRL.makePipelineParser(pipelineFolder, commandLineOptions, 0.000001,
					printer.outputsDependencies());
			parser2 = new BackoffSRLParser(new JointSRLParser(EasySRL.getParserBuilder(commandLineOptions).build(),
					posTagger), pipeline);
		} else {
			// Pipeline
			parser2 = EasySRL.makePipelineParser(modelFolder, commandLineOptions, 0.000001, printer.outputsDependencies());
		}

		this.reader = InputReader.make(EasySRL.InputFormat.valueOf(commandLineOptions.getInputFormat().toUpperCase()));
		if ((outputFormat == EasySRL.OutputFormat.PROLOG || outputFormat == EasySRL.OutputFormat.EXTENDED)
				&& input != EasySRL.InputFormat.POSANDNERTAGGED) {
			String msg = "Must use \"-i POSandNERtagged\" for this output";
			logger.error(msg);
			throw new Error(msg);
		}
		logger.debug("Model loaded: gRPC parser ready");

		infer_lock.lock(); // limit concurrency because EasySRL is not thread-safe
		this.parser = parser2;
		infer_lock.unlock();
	}

	public String parse(String sentence) {
		if (parser != null) {
			List<CCGandSRLparse> parses = parser.parseTokens(reader.readInput(sentence)
					.getInputWords());
			return printer.printJointParses(parses, -1);
		}
		return "";
	}

	@Override
	/** {@inheritDoc} */
	public void create(Request request, StreamObserver<Empty> responseObserver) {
		logger.debug(">> CREATE; User: " + request.getLUCID());
		responseObserver.onNext(Empty.newBuilder().build());
		responseObserver.onCompleted();
	}

	@Override
	/** {@inheritDoc} */
	public void learn(Request request, StreamObserver<Empty> responseObserver) {
		logger.debug(">> LEARN; User: " + request.getLUCID());

		responseObserver.onNext(Empty.newBuilder().build());
		responseObserver.onCompleted();
	}

	@Override
	/** {@inheritDoc} */
    public void infer(Request request, StreamObserver<Response> responseObserver) {
		logger.debug(">> INFER; User: " + request.getLUCID());
		
	    if (request.getSpec().getContentList().isEmpty() || 
                request.getSpec().getContentList().get(0).getDataList().isEmpty()) {
            logger.info("empty content passed to service");
	        throw new IllegalArgumentException();
	    }

		try {
			QueryInput queryInput = request.getSpec().getContentList().get(0);

			infer_lock.lock(); // limit concurrency because EasySRL is not thread-safe

			// FIXME: Response.msg should be an array
			// Only look for the first item in content and data.
			// The rest part of query is ignored.
			final StringBuilder output = new StringBuilder();
			for (int i = 0; i < queryInput.getDataList().size(); ++i) {
				String sentence = queryInput.getDataList().get(i).toString("UTF-8");
				output.append(parse(sentence));
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
			infer_lock.unlock(); // always unlock at the end
		}
	}
}
