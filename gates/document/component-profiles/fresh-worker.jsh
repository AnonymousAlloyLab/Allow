// One untimed parent warmup, then five freshly sandboxed validation JVMs.
// Measures existing unchanged launcher and FrameProcess; prints only time and byte count.
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
{
 var ctor=Class.forName("dev.allow.backend.BubblewrapLauncher").getDeclaredConstructor(Path.class, boolean.class);
 var launch=Class.forName("dev.allow.backend.BubblewrapLauncher").getDeclaredMethod("launch");
 var exchange=Class.forName("dev.allow.backend.FrameProcess").getDeclaredMethod("exchange",Process.class,byte[].class,int.class,long.class);
 ctor.setAccessible(true);launch.setAccessible(true);exchange.setAccessible(true);
 var input=Files.readAllBytes(Path.of(".runtime/documents/validator-profile-input.json"));
 for(int i=0;i<6;i++) {
  long start=System.nanoTime(); var launcher=ctor.newInstance(Path.of("backend/target"),true);long constructed=System.nanoTime();
  var child=(Process)launch.invoke(launcher);long launched=System.nanoTime();
  var output=(byte[])exchange.invoke(null,child,input,1048577,10000L);long finished=System.nanoTime();
  if(!new String(output,StandardCharsets.UTF_8).contains("\"status\":\"VALIDATED\"")) throw new IllegalStateException("Profile validation failed");
  if(i>0) System.out.println("PROFILE_MS="+(constructed-start)/1000000.0+","+(launched-constructed)/1000000.0+","+(finished-launched)/1000000.0+","+(finished-start)/1000000.0+" OUTPUT_BYTES="+output.length);
 }
}
/exit
