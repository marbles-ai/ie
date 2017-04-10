package uk.ac.ed.easyccg.main;

import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.text.DecimalFormat;
import java.util.Collection;
import java.util.InputMismatchException;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Scanner;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.nio.file.Path;
import java.nio.file.FileSystems;

import ai.marbles.grpc.ServiceAcceptor;
import uk.co.flamingpenguin.jewel.cli.ArgumentValidationException;
import uk.co.flamingpenguin.jewel.cli.CliFactory;
import uk.co.flamingpenguin.jewel.cli.Option;

import com.google.common.base.Stopwatch;

import uk.ac.ed.easyccg.syntax.Category;
import uk.ac.ed.easyccg.syntax.InputReader;
import uk.ac.ed.easyccg.syntax.ParsePrinter;
import uk.ac.ed.easyccg.syntax.Parser;
import uk.ac.ed.easyccg.syntax.ParserAStar;
import uk.ac.ed.easyccg.syntax.ParserAStar.SuperTaggingResults;
import uk.ac.ed.easyccg.syntax.SyntaxTreeNode;
import uk.ac.ed.easyccg.syntax.SyntaxTreeNode.SyntaxTreeNodeFactory;
import uk.ac.ed.easyccg.syntax.TagDict;
import uk.ac.ed.easyccg.syntax.TaggerEmbeddings;
import uk.co.flamingpenguin.jewel.cli.ArgumentValidationException;
import uk.co.flamingpenguin.jewel.cli.CliFactory;
import uk.co.flamingpenguin.jewel.cli.Option;

public class EasyCCG
{
  
  /**
   * Command Line Interface
   */
  public interface CommandLineArguments  
  {
    @Option(shortName="m", description = "Path to the parser model")
    File getModel();

    @Option(shortName="f", defaultValue="", description = "(Optional) Path to the input text file. Otherwise, the parser will read from stdin.")
    File getInputFile();

    @Option(shortName="i", defaultValue="tokenized", description = "(Optional) Input Format: one of \"tokenized\", \"POStagged\", \"POSandNERtagged\", \"gold\" or \"supertagged\"")
    String getInputFormat();
    
    @Option(shortName="o", description = "Output Format: one of \"ccgbank\", \"html\", or \"prolog\"", defaultValue="ccgbank")
    String getOutputFormat();

    // Missing -a from easySRL (choose parsing algorithm)

    @Option(shortName="l", defaultValue="70", description = "(Optional) Maximum length of sentences in words. Defaults to 70.")
    int getMaxLength();

    @Option(shortName="n", defaultValue="1", description = "(Optional) Number of parses to return per sentence. Defaults to 1.")
    int getNbest();

    @Option(shortName="r", defaultValue={"S[dcl]", "S[wq]", "S[q]", "S[qem]", "NP"}, description = "(Optional) List of valid categories for the root node of the parse. Defaults to: S[dcl] S[wq] S[q] NP")
    List<String> getRootCategories();

    // Extra -s for additional, unrestricted rules

    @Option(shortName="s", description = "(Optional) Allow rules not involving category combinations seen in CCGBank. Slows things down by around 20%.")
    boolean getUnrestrictedRules();

    // Supertaggerbeam is 0.01 of that in easySrl!

    @Option(defaultValue="0.0001", description = "(Optional) Prunes lexical categories whose probability is less than this ratio of the best category. Defaults to 0.0001.")
    double getSupertaggerbeam();
    
    @Option(defaultValue="0.0", description = "(Optional) If using N-best parsing, filter parses whose probability is lower than this fraction of the probability of the best parse. Defaults to 0.0")
    double getNbestbeam();

    // Missing SuperTaggerWeight

    @Option(helpRequest = true, description = "Display this message", shortName = "h")
    boolean getHelp();

    @Option(shortName = "d", description = "Run as a gRPC daemon.")
    boolean getDaemonize();

    @Option(shortName = "p", defaultValue = "8084", description = "Set the port to listen for gRPC connection. Only valid with --daemonize option.")
    int getPort();
    
    @Option(description = "(Optional) Make a tag dictionary")
    boolean getMakeTagDict();

  }
  
  // Supports same input formats as EasySRL
  public enum InputFormat {
    TOKENIZED, GOLD, SUPERTAGGED, POSTAGGED, POSANDNERTAGGED
  }
  
  public enum OutputFormat {

    // Fewer available output formats; add as are needed
    CCGBANK(ParsePrinter.CCGBANK_PRINTER), HTML(ParsePrinter.HTML_PRINTER), SUPERTAGS(ParsePrinter.SUPERTAG_PRINTER),
    PROLOG(ParsePrinter.PROLOG_PRINTER), EXTENDED(ParsePrinter.EXTENDED_CCGBANK_PRINTER);
    
    public final ParsePrinter printer;

    OutputFormat(ParsePrinter printer) {
      this.printer = printer;
    }
  }
  
  public static void main(String[] args) throws IOException, InterruptedException, ArgumentValidationException {
    
    
    CommandLineArguments parsedArgs = CliFactory.parseArguments(CommandLineArguments.class, args);
    InputFormat input = InputFormat.valueOf(parsedArgs.getInputFormat().toUpperCase());
    
    if (parsedArgs.getMakeTagDict()) {
      InputReader reader = InputReader.make(input, new SyntaxTreeNodeFactory(parsedArgs.getMaxLength(), 0));
      Map<String, Collection<Category>> tagDict = TagDict.makeDict(reader.readFile(parsedArgs.getInputFile()));
      TagDict.writeTagDict(tagDict, parsedArgs.getModel());
      System.exit(0);
    }
    
    
    if (!parsedArgs.getModel().exists()) throw new InputMismatchException("Couldn't load model from from: " + parsedArgs.getModel());
    System.err.println("Loading model...");

    // Added for daemon
        // PWG: run as a gRPC service
    if (parsedArgs.getDaemonize()) {
        CcgServiceHandler svc = new CcgServiceHandler(parsedArgs);
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

        ServiceAcceptor server = new ServiceAcceptor(parsedArgs.getPort(), svc);
        server.start();
        System.out.println("EasyCCG at port " + parsedArgs.getPort());
        server.blockUntilShutdown();
        return;
    }


    
    Parser parser = new ParserAStar(
        new TaggerEmbeddings(parsedArgs.getModel(), parsedArgs.getMaxLength(), parsedArgs.getSupertaggerbeam()), 
        parsedArgs.getMaxLength(),
        parsedArgs.getNbest(),
        parsedArgs.getNbestbeam(),
        input,
        parsedArgs.getRootCategories(),
        new File(parsedArgs.getModel(), "unaryRules"),
        new File(parsedArgs.getModel(), "binaryRules"),
        parsedArgs.getUnrestrictedRules() ? null : new File(parsedArgs.getModel(), "seenRules")
        );

    OutputFormat outputFormat = OutputFormat.valueOf(parsedArgs.getOutputFormat().toUpperCase());
    ParsePrinter printer = outputFormat.printer;

    if ((outputFormat == OutputFormat.PROLOG || outputFormat == OutputFormat.EXTENDED) && input != InputFormat.POSANDNERTAGGED) throw new Error("Must use \"-i POSandNERtagged\" for this output");
    
    if (!parsedArgs.getInputFile().getName().isEmpty()) {
      System.err.println("Parsing...");

      // Read from file
      Stopwatch t = Stopwatch.createStarted();
      SuperTaggingResults results = new SuperTaggingResults();
      Iterator<List<SyntaxTreeNode>> parsesIt = parser.parseFile(parsedArgs.getInputFile(), results);
      
      while (parsesIt.hasNext()) {
        List<SyntaxTreeNode> parse = parsesIt.next();
        System.out.println(printer.print(parse, results.totalSentences));
      }
      
      DecimalFormat twoDP = new DecimalFormat("#.##");
      System.err.println("Coverage: " + twoDP.format(100.0 * results.parsedSentences / results.totalSentences) + "%");
      if (results.totalCats > 0) {
        System.err.println("Accuracy: " + twoDP.format(100.0 * results.rightCats / results.totalCats) + "%");
      }

      System.err.println("Sentences parsed: " + results.parsedSentences);
      System.err.println("Speed: " + twoDP.format(1000.0 * results.parsedSentences / t.elapsed(TimeUnit.MILLISECONDS)) + " sentences per second");
    } else {
      // Read from stdin
      Scanner sc = new Scanner(System.in,"UTF-8");
      System.err.println("Model loaded, ready to parse.");

      int id = 0;
      while(sc.hasNext()) {
        String line = sc.nextLine().trim();
        List<SyntaxTreeNode> parses = parser.parse(line);
        id++;
        if (parses == null) continue ;
        System.out.println(printer.print(parses, id));
      }
    }
  }

    static void daemonize(String modelPath) throws IOException, InterruptedException {
        CcgServiceHandler svc = new CcgServiceHandler("~/src/ie/ext/easyccg/model/text");
        svc.init();
        ServiceAcceptor server = new ServiceAcceptor(8085, svc);
        server.start();
        System.out.println("EasyCCG at port 8085");
        server.blockUntilShutdown();

    }

}
