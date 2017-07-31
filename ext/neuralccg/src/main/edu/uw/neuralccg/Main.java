package edu.uw.neuralccg;

import com.google.common.base.Stopwatch;
import com.google.common.collect.ImmutableList;

import ai.marbles.grpc.ServiceAcceptor;
import ai.marbles.aws.log4j.CloudwatchAppender;

import com.google.protobuf.Any;
import com.hp.gagawa.java.elements.Br;
import com.hp.gagawa.java.elements.Pre;
import com.typesafe.config.Config;
import com.typesafe.config.ConfigFactory;
import com.typesafe.config.ConfigResolveOptions;
import edu.uw.easysrl.main.EasySRL;
import edu.uw.easysrl.main.InputReader;
import edu.uw.easysrl.main.ParsePrinter;
import edu.uw.easysrl.syntax.grammar.Category;
import edu.uw.easysrl.syntax.grammar.SyntaxTreeNode;
import edu.uw.easysrl.syntax.tagger.Tagger;
import edu.uw.easysrl.syntax.tagger.TaggerEmbeddings;
import edu.uw.easysrl.util.Util;
import edu.uw.easysrl.syntax.parser.Parser;
import edu.uw.easysrl.main.InputReader.InputToParser;
import edu.uw.easysrl.util.Util.Scored;

import edu.uw.neuralccg.model.TreeFactoredModel;
import edu.uw.neuralccg.util.EasySRLUtil;

import edu.uw.neuralccg.util.GateUtil;
import edu.uw.neuralccg.util.SyntaxUtil;
import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;
import org.apache.log4j.PatternLayout;
import org.apache.log4j.Priority;

import uk.co.flamingpenguin.jewel.cli.ArgumentValidationException;
import uk.co.flamingpenguin.jewel.cli.CliFactory;
import uk.co.flamingpenguin.jewel.cli.Option;

import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.text.DecimalFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;
import java.util.stream.Collectors;

public class Main {
	private static final Logger logger = LogManager.getLogger(Main.class);
	/**
	 * Command Line Interface
	 */
	public interface CommandLineArguments {
		@Option(shortName = "m", description = "Path to the parser model")
		String getModel();

		@Option(shortName = "c", description = "Path to the config file")
		String getConfig();

		@Option(shortName = "f", defaultValue = "", description = "(Optional) Path to the input text file. Otherwise, the parser will read from stdin.")
		String getInputFile();

		@Option(helpRequest = true, description = "Display this message.", shortName = "h")
		boolean getHelp();

		@Option(shortName = "d", description = "Run as a gRPC daemon.")
		boolean getDaemonize();

		@Option(shortName = "p", defaultValue = "8090", description = "Set the port to listen for gRPC connection. Only valid with --daemonize option.")
		int getPort();

		@Option(shortName = "A", defaultValue = "neuralccg", description = "(Optional) AWS log stream name")
		String getAwsLogStream();
	}

	public static void main(String[] args) throws IOException, InterruptedException {
		try {
			final CommandLineArguments commandLineOptions = CliFactory.parseArguments(CommandLineArguments.class, args);
			//final InputFormat input = InputFormat.valueOf(commandLineOptions.getInputFormat().toUpperCase());
			final File modelFolder = Util.getFile(EasySRL.absolutePath(commandLineOptions.getModel()));
			final File configFile = Util.getFile(EasySRL.absolutePath(commandLineOptions.getConfig()));

			if (!modelFolder.exists()) {
				throw new InputMismatchException("Couldn't load model from from: " + modelFolder.toString());
			}

			if (!configFile.exists()) {
				throw new InputMismatchException("Couldn't load config from from: " + configFile.toString());
			}

			Config parameters = ConfigFactory.parseFileAnySyntax(configFile)
					.resolve(ConfigResolveOptions.defaults().setAllowUnresolved(true));

			if (commandLineOptions.getDaemonize()) {
				// PWG: run as a gRPC service
				// Modify AWS Cloudlogger
				PatternLayout layout = new org.apache.log4j.PatternLayout();
				layout.setConversionPattern("%p %d{yyyy-MM-dd HH:mm:ssZ} %c [%t] - %m%n");
				CloudwatchAppender cloudwatchAppender = new CloudwatchAppender(layout, "core-nlp-services", commandLineOptions.getAwsLogStream());
				cloudwatchAppender.setThreshold(Priority.INFO);
				Logger.getRootLogger().addAppender(cloudwatchAppender);

				// Now start service
				CcgServiceHandler svc = new CcgServiceHandler(commandLineOptions, parameters);
				logger.info("starting gRPC CCG parser service...");
				// Want start routine to exit quickly else connections to gRPC service fail.
				ExecutorService executorService = Executors.newFixedThreadPool(1);
				executorService.execute(new Runnable() {
					@Override
					public void run() {
						try {
							svc.init();
						} catch (Exception e) {
							throw new RuntimeException(e);
						}
					}
				});

				ServiceAcceptor server = new ServiceAcceptor(commandLineOptions.getPort(), svc);
				server.start();
				logger.info("gRPC CCG parser service started on port " + commandLineOptions.getPort());

				Runtime.getRuntime().addShutdownHook(new Thread() {
					@Override
					public void run()
					{
						logger.info("Shutdown signal received");
						server.shutdown();
						try {
							if (server.blockUntilShutdown(5000)) {
								logger.info("Server shutdown complete");
							} else {
								logger.info("Server shutdown not complete after 5 seconds, exiting now.");
							}
						} catch (InterruptedException e) {
						}
						LogManager.shutdown();
					}
				});
				server.blockUntilShutdown();
				return;
			}

			final InputReader reader = InputReader.make(EasySRL.InputFormat.TOKENIZED);
			final boolean readingFromStdin;
			final Iterator<String> inputLines;
			if (commandLineOptions.getInputFile().isEmpty()) {
				// Read from STDIN
				inputLines = new Scanner(System.in, "UTF-8");
				readingFromStdin = true;
			} else {
				// Read from file
				inputLines = Util.readFile(Util.getFile(commandLineOptions.getInputFile())).iterator();
				readingFromStdin = false;
			}

			Parser parser = initializeModel(parameters, EasySRL.absolutePath(commandLineOptions.getModel()));
			ParsePrinter printer = ParsePrinter.CCGBANK_PRINTER;
			System.err.println("===Model loaded: parsing...===");

			final Stopwatch timer = Stopwatch.createStarted();
			final AtomicInteger parsedSentences = new AtomicInteger();
			final ExecutorService executorService = Executors.newFixedThreadPool(1);

			final BufferedWriter sysout = new BufferedWriter(new OutputStreamWriter(System.out));

			int id = 0;
			while (inputLines.hasNext()) {
				// Read each sentence, either from STDIN or a parse.
				final String sentence = inputLines instanceof Scanner ? ((Scanner) inputLines).nextLine().trim()
					: inputLines.next();
				if (!sentence.isEmpty() && !sentence.startsWith("#")) {
					id++;
					final int id2 = id;

					// Make a new ExecutorService job for each sentence to parse.
					executorService.execute(new Runnable() {
						@Override
						public void run() {
							final InputToParser input = InputToParser.fromTokens(Arrays.asList(sentence.split(" ")));
							synchronized (printer) {
								try {
									// List of nbest-parse root nodes
									final List<Scored<SyntaxTreeNode>> result = parser.doParsing(input);
									if (result != null) {
										parsedSentences.getAndIncrement();
										List<SyntaxTreeNode> lst = result.stream()
												.map(p -> p.getObject())
												.collect(Collectors.toList());
										final String output = printer.print(lst, -1);

										sysout.write(output);
										sysout.newLine();

										if (readingFromStdin) {
											sysout.flush();
										}
									} else {
										sysout.write("Parse failed.");
									}
								} catch (final IOException e) {
									throw new RuntimeException(e);
								}
							}
						}
					});
				}
			}
			executorService.shutdown();
			executorService.awaitTermination(Long.MAX_VALUE, TimeUnit.DAYS);
			sysout.close();

			final DecimalFormat twoDP = new DecimalFormat("#.##");

			System.err.println("Sentences parsed: " + parsedSentences.get());
			System.err.println("Speed: "
				+ twoDP.format(1000.0 * parsedSentences.get() / timer.elapsed(TimeUnit.MILLISECONDS))
				+ " sentences per second");

		} catch (final ArgumentValidationException e) {
			System.err.println(e.getMessage());
		}
		System.exit(0);
    }

	public static Parser initializeModel(Config parameters, String modelDir) {
		final File modelFolder = new File(modelDir);
		final File checkpointPath = new File(modelFolder, "llz2016.model.pb");
		TreeFactoredModel.TreeFactoredModelFactory modelFactory;
		Parser parser;

        logger.info(String.format("Loading model from %s ...", modelDir));
		final Collection<Category> categories;
		try {
			categories = TaggerEmbeddings.loadCategories(new File(modelFolder, "categories"));
		} catch (IOException e) {
			throw new RuntimeException(e);
		}

        final Config args = parameters.getConfig("demo.args");
		final Tagger tagger = EasySRLUtil.loadTagger(args, modelDir);

		TreeFactoredModel.TreeFactoredModelFactory.initializeCNN(TrainProto.RunConfig.newBuilder()
			.setMemory(args.getInt("native_memory")).build());

		synchronized (TreeFactoredModel.TreeFactoredModelFactory.class) {
			modelFactory = new TreeFactoredModel.TreeFactoredModelFactory(
				Optional.of(tagger),
				categories,
				args,
				true,
				true,
				Optional.empty(),
				checkpointPath,
				Optional.empty(),
				Optional.empty());

			parser = EasySRLUtil.parserBuilder(args, modelDir)
				.modelFactory(modelFactory)
				.listeners(Collections.singletonList(modelFactory))
				.build();
		}
		return parser;
	}
}
