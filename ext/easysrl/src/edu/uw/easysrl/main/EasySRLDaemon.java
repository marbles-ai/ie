package ai.marbles.easysrl;

import ai.marbles.grpc.ServiceAcceptor;
import edu.uw.easysrl.main.CcgServiceHandler;

/**
 * Starts the EasySRL CCG server and listens for requests.
 */
public class EasySRLDaemon {
	/** 
	 * Entry point for question-answer.
	 * @param args the argument list. Provide port numbers
	 * for both sirius and qa.
	 */
	public static void main(String[] args) throws Exception {
		CcgServiceHandler svc = new CcgServiceHandler("/Users/paul/EasySRL/model/text");
		svc.init();
		ServiceAcceptor server = new ServiceAcceptor(8084, svc);
		server.start();
		System.out.println("EasySRL at port 8084");
		server.blockUntilShutdown();
	}
}
