package dev.allow.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** Local Spring entry point; the parent process never loads the Alloy engine. */
@SpringBootApplication
public class AllowApplication {
    /**
     * Starts the loopback application.
     * @param arguments Spring configuration arguments
     */
    public static void main(String[] arguments) {
        SpringApplication.run(AllowApplication.class, arguments);
    }
}
