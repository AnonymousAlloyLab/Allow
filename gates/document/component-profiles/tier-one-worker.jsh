// Exploratory component timing only: fresh JVM, unchanged sandbox limits, one JIT flag.
// Not production policy or end-to-end acceptance; no application source is modified.
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
{
 var ctor=Class.forName("dev.allow.backend.BubblewrapLauncher").getDeclaredConstructor(Path.class, boolean.class);
 var command=Class.forName("dev.allow.backend.BubblewrapLauncher").getDeclaredMethod("command",Path.class);
 var exchange=Class.forName("dev.allow.backend.FrameProcess").getDeclaredMethod("exchange",Process.class,byte[].class,int.class,long.class);
 ctor.setAccessible(true);command.setAccessible(true);exchange.setAccessible(true);
 var input=Files.readAllBytes(Path.of(".runtime/documents/validator-profile-input.json"));
 for(int i=0;i<6;i++) {
  long start=System.nanoTime(); var launcher=ctor.newInstance(Path.of("backend/target"),true);long constructed=System.nanoTime();
  var args=new ArrayList<String>((List<String>)command.invoke(launcher,Path.of("backend/target/solver/alloy.jar").toAbsolutePath()));
  args.add(args.indexOf("-Xmx512m"),"-XX:TieredStopAtLevel=1");
  var builder=new ProcessBuilder(args);builder.environment().clear();builder.directory(Path.of("backend/target").toFile());
  var child=builder.start();long launched=System.nanoTime();
  var output=(byte[])exchange.invoke(null,child,input,1048577,10000L);long finished=System.nanoTime();
  if(!new String(output,StandardCharsets.UTF_8).contains("\"status\":\"VALIDATED\"")) throw new IllegalStateException("Profile validation failed");
  if(i>0) System.out.println("PROFILE_MS="+(constructed-start)/1000000.0+","+(launched-constructed)/1000000.0+","+(finished-launched)/1000000.0+","+(finished-start)/1000000.0+" OUTPUT_BYTES="+output.length);
 }
}
/exit
