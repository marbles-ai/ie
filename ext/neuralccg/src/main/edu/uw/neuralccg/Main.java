package edu.uw.neuralccg;

import com.google.common.base.Stopwatch;
import com.google.common.collect.ImmutableList;

import ai.marbles.grpc.ServiceAcceptor;
import ai.marbles.aws.log4j.CloudwatchAppender;

import com.google.protobuf.Any;
import com.typesafe.config.Config;
import edu.uw.easysrl.main.EasySRL;
import edu.uw.easysrl.syntax.grammar.Category;
import edu.uw.easysrl.syntax.parser.SRLParser;
import edu.uw.easysrl.syntax.tagger.Tagger;
import edu.uw.easysrl.syntax.tagger.TaggerEmbeddings;
import edu.uw.easysrl.util.Util;

import edu.uw.neuralccg.model.TreeFactoredModel;
import edu.uw.neuralccg.util.EasySRLUtil;
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

public class Main {
	private static final Logger logger = LogManager.getLogger(Main.class);
	/**
	 * Command Line Interface
	 */
	public interface CommandLineArguments {
		@Option(shortName = "m", description = "Path to the parser model")
		String getModel();

		@Option(shortName = "m", description = "Path to the config file")
		String getConfig();

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
			final InputFormat input = InputFormat.valueOf(commandLineOptions.getInputFormat().toUpperCase());
			final File modelFolder = Util.getFile(absolutePath(commandLineOptions.getModel()));

			if (!modelFolder.exists()) {
				throw new InputMismatchException("Couldn't load model from from: " + modelFolder);
			}

			// PWG: run as a gRPC service
			if (commandLineOptions.getDaemonize()) {
				// Modify AWS Cloudlogger
				PatternLayout layout = new org.apache.log4j.PatternLayout();
				layout.setConversionPattern("%p %d{yyyy-MM-dd HH:mm:ssZ} %c [%t] - %m%n");
				CloudwatchAppender cloudwatchAppender = new CloudwatchAppender(layout, "core-nlp-services", commandLineOptions.getAwsLogStream());
				cloudwatchAppender.setThreshold(Priority.INFO);
				Logger.getRootLogger().addAppender(cloudwatchAppender);

				// Now start service
				CcgServiceHandler svc = new CcgServiceHandler(commandLineOptions);
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
			System.err.println("===Model loaded: parsing...===");

			final Stopwatch timer = Stopwatch.createStarted();
			final AtomicInteger parsedSentences = new AtomicInteger();
			final ExecutorService executorService = Executors.newFixedThreadPool(1);

			final BufferedWriter sysout = new BufferedWriter(new OutputStreamWriter(System.out));

			int id = 0;
			while (inputLines.hasNext()) {
				// Read each sentence, either from STDIN or a parse.
				final String line = inputLines instanceof Scanner ? ((Scanner) inputLines).nextLine().trim()
					: inputLines.next();
				if (!line.isEmpty() && !line.startsWith("#")) {
					id++;
					final int id2 = id;

					// Make a new ExecutorService job for each sentence to parse.
					executorService.execute(new Runnable() {
						@Override
						public void run() {

							final List<SRLParser.CCGandSRLparse> parses = parser.parseTokens(reader.readInput(line)
								.getInputWords());
							final String output = printer.printJointParses(parses, id2);
							parsedSentences.getAndIncrement();
							synchronized (printer) {
								try {
									// It's a bit faster to buffer output than use
									// System.out.println() directly.
									sysout.write(output);
									sysout.newLine();

									if (readingFromStdin) {
										sysout.flush();
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
			System.err.println(CliFactory.createCli(EasySRL.CommandLineArguments.class).getHelpMessage());
		}
    }

	public void initializeModel(Config parameters, File modelFolder) {
		final File checkpointPath = new File(modelFolder, "llz2016.model.pb");

		final Collection<Category> categories;
		try {
			categories = TaggerEmbeddings.loadCategories(new File(modelFolder, "categories"));
		} catch (IOException e) {
			throw new RuntimeException(e);
		}

		final Tagger tagger = EasySRLUtil.loadTagger(parameters);

		TreeFactoredModel.TreeFactoredModelFactory.initializeCNN(TrainProto.RunConfig.newBuilder()
			.setMemory(parameters.getInt("native_memory")).build());

		synchronized (TreeFactoredModel.TreeFactoredModelFactory.class) {
			modelFactory = new TreeFactoredModel.TreeFactoredModelFactory(
				Optional.of(tagger),
				categories,
				parameters,
				true,
				true,
				Optional.empty(),
				checkpointPath,
				Optional.empty(),
				Optional.empty());

			parser = EasySRLUtil.parserBuilder(parameters)
				.modelFactory(modelFactory)
				.listeners(Collections.singletonList(modelFactory))
				.build();

			try {
				while (true) {
					Thread.sleep(Long.MAX_VALUE);
				}
			} catch (final InterruptedException e) {
				throw new RuntimeException(e);
			}
		}
	}

}
