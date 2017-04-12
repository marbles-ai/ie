package ai.marbles.eayccg;

import uk.ac.ed.easyccg.main.CcgServiceHandler;
import static org.junit.Assert.*;
import org.junit.Test;

/**
 * Created by paul on 2/15/17.
 */
public class CcgServiceHandlerTest {

    @Test
    public void testParser() {
        try {
            CcgServiceHandler svc = new CcgServiceHandler("~/easyccg-0.2/model/text");
            svc.init();

            String expected = "(<T S[dcl] 1 2> (<L NP PRP PRP It NP>) (<T S[dcl]\\NP 0 2> (<L (S[dcl]\\NP)/NP VBZ VBZ is (S[dcl]\\NP)/NP>) (<T NP 0 2> (<L NP/N PRP$ PRP$ my NP/N>) (<T N 1 2> (<L N/N JJ JJ first N/N>) (<T N 0 2> (<L N/PP NN NN morning N/PP>) (<T PP 0 2> (<L PP/NP IN IN of PP/NP>) (<T NP 0 1> (<T N 1 2> (<L N/N JJ JJ high N/N>) (<L N NN NN school. N>) ) ) ) ) ) ) ) )";
            String result = svc.parse("It is my first morning of high school.").replaceFirst("\\s+$","");
            assertEquals(expected, result);

        } catch (Exception e) {
            fail(e.getMessage());
        }
    }
}
