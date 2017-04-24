package uk.ac.ed.easyccg.main;

// Java packages
import java.io.*;
import java.util.*;
import java.io.File;

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

import uk.ac.ed.easyccg.main.EasyCCG.CommandLineArguments;
import uk.ac.ed.easyccg.main.EasyCCG.OutputFormat;

import uk.ac.ed.easyccg.syntax.InputReader;
import uk.ac.ed.easyccg.syntax.ParsePrinter;

import uk.ac.ed.easyccg.syntax.Parser;
import uk.ac.ed.easyccg.syntax.Category;





/**
 * Test interface.
 */
public class CcgServiceHandler extends LucidaServiceGrpc.LucidaServiceImplBase {

	public interface Session {
		Parser getParser();
		InputReader getReader();
		ParsePrinter getPrinter();
		OutputFormat getOutputFormat();
		void lock();
		void unlock();
	}

	public class ConfigOptions implements CommandLineArguments {
		private String modelPath;

		ConfigOptions(String modelPath) { this.modelPath = modelPath; }

		public File getModel() { return new File(modelPath); }

		public File getInputFile() { return new File(""); }

		// defaultValue = "tokenized", description = "(Optional) Input Format: one of \"tokenized\", \"POStagged\" (word|pos), or \"POSandNERtagged\" (word|pos|ner)")
		public String getInputFormat() { return "tokenized"; }

		public String getOutputFormat() { return "ccgbank"; }

		public String getParsingAlgorithm() { return "astar"; }

		// "(Optional) Maximum length of sentences in words. Defaults to 70.")
		public int getMaxLength() { return 70; }

		// "(Optional) Number of parses to return per sentence. Values >1 are only supported for A* parsing. Defaults to 1.")
		public int getNbest() { return 1; }

		// defaultValue = { "S[dcl]", "S[wq]", "S[q]", "S[b]\\NP", "NP" }, description = "(Optional) List of valid categories for the root node of the parse. Defaults to: S[dcl] S[wq] S[q] NP S[b]\\NP")
		public List<String> getRootCategories() {
			ArrayList<String> list = new ArrayList<>(5);
			list.add("S[dcl]");
			list.add("S[wq]");
			list.add("S[q]");
			list.add("S[b]\\NP");
			list.add("NP");
			return list;
		}

		// defaultValue = "0.01", description = "(Optional) Prunes lexical categories whose probability is less than this ratio of the best category. Decreasing this value will slightly improve accuracy, and give more varied n-best output, but decrease speed. Defaults to 0.01 (currently only used for the joint model).")
		public double getSupertaggerbeam() { return 0.01; }

		// defaultValue = "1.0", description = "Use a specified supertagger weight, instead of the pretrained value.")
		public double getSupertaggerWeight() { return 1.0; }

		public boolean getHelp() { return true; }

		public boolean getDaemonize() { return true; }

		public int getPort() { return 8084; }

		/*
		    Not in EasySRL
		 */
        public boolean getMakeTagDict() {
            return false;
        };

        public double getNbestbeam(){
            return 0.0;
        };

        public boolean getUnrestrictedRules(){
            return false;
        };
    }

	public CcgServiceHandler(String pathToModel) {
		commandLineOptions_ = new ConfigOptions(pathToModel);
	}
    public CcgServiceHandler() {
    }


    private HashMap<String, Session> sessionCache_ = new HashMap();
	private CommandLineArguments commandLineOptions_;
	private Session defaultSession_;

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