package ai.marbles.easyccg;

import ai.marbles.grpc.ServiceAcceptor;
import ai.marbles.grpc.ServiceConnector;
import ai.marbles.grpc.Request;
import uk.ac.ed.easyccg.main.CcgServiceHandler;
import static org.junit.Assert.*;
import org.junit.Test;

/*
 * A testing Client that sends a single query to EasyCCG Server and prints the results.
 */
public class EasyCCGDaemonTest {

	@Test
	public void testClientServer() {
		// Collect the port number.
		int port = 9083;

		// User.
		String LUCID = "EasyCCGDaemonTest";
		ServiceAcceptor server = null;
		try {

			System.out.println("Starting EasyCCGDaemonTest...");
			CcgServiceHandler svc = new CcgServiceHandler("~/easyccg-0.2/model/text");
			svc.init();
			server = new ServiceAcceptor(port, svc);
			server.start();
			System.out.println("EasyCCG parser service at port " + port);

			ServiceConnector client = new ServiceConnector("localhost", port);
			Request request;

			client.create(LUCID);

			request = client.buildInferRequest(LUCID, "text", "It is my first morning of high school.");
			// Print the question
			System.out.println(request.getSpec().getContent(0).getData(0).toString("UTF-8"));
			String answer = client.infer(request).replaceFirst("\\s+$", "");
			String expected = "(<T S[dcl] 1 2> (<L NP PRP PRP It NP>) (<T S[dcl]\\NP 0 2> (<L (S[dcl]\\NP)/NP VBZ VBZ is (S[dcl]\\NP)/NP>) (<T NP 0 2> (<L NP/N PRP$ PRP$ my NP/N>) (<T N 1 2> (<L N/N JJ JJ first N/N>) (<T N 0 2> (<L N/PP NN NN morning N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ high N/N>) (<L N NN NN school. N>) ) ) ) ) ) ) ) )";
			// Print the answer.
			assertEquals(expected, answer);

			client.shutdown();
			assertTrue(client.blockUntilShutdown(3000));
		} catch (Exception e) {
			fail(e.getMessage());
		}
		try {
			if (server != null) {
				server.shutdown();
				assertTrue(server.blockUntilShutdown(3000));
			}
		} catch (Exception e) {
			fail(e.getMessage());
		}
	}
}
