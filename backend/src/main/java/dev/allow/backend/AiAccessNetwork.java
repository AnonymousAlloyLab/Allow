package dev.allow.backend;

import dev.allow.worker.JsonWire;
import jakarta.mail.Message;
import jakarta.mail.Session;
import jakarta.mail.Transport;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Properties;

/** Fixed Google verification and authenticated STARTTLS mail transport. */
final class AiAccessNetwork implements AiAccessTransport {
    private final AiAccessConfig config;
    private final Clock clock;
    private final HttpClient client;
    /** Stores validated configuration and bounded HTTP client.
     * @param config protected settings
     * @param clock time source
     */
    AiAccessNetwork(AiAccessConfig config, Clock clock) {
        this.config = config;
        this.clock = clock;
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).followRedirects(HttpClient.Redirect.NEVER).build();
    }
    /** Verifies fixed-host Google output with strict bounds.
     * @param token opaque token
     * @return verified current result
     */
    @Override
    public boolean captcha(String token) {
        try {
            String body = "secret=" + URLEncoder.encode(config.captchaSecret(), StandardCharsets.UTF_8)
                    + "&response=" + URLEncoder.encode(token, StandardCharsets.UTF_8);
            HttpRequest request = HttpRequest.newBuilder(URI.create("https://www.google.com/recaptcha/api/siteverify"))
                    .timeout(Duration.ofSeconds(5)).header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString(body)).build();
            HttpResponse<byte[]> response = bounded(client, request);
            if (response.statusCode() != 200) return false;
            Map<?, ?> result = JsonWire.decode(response.body(), Map.class);
            if (!Boolean.TRUE.equals(result.get("success")) || !config.hostname().equals(result.get("hostname"))) return false;
            Object timestamp = result.get("challenge_ts");
            if (!(timestamp instanceof String text)) return false;
            Instant at = Instant.parse(text);
            return !at.isBefore(clock.instant().minusSeconds(120)) && !at.isAfter(clock.instant().plusSeconds(30));
        } catch (Exception failure) { return false; }
    }
    /** Bounds total elapsed response time including a stalled body.
     * @param client bounded client
     * @param request fixed provider request
     * @return complete bounded response
     * @throws Exception timeout or provider failure
     */
    static HttpResponse<byte[]> bounded(HttpClient client, HttpRequest request) throws Exception {
        var future = client.sendAsync(request, AiAccessBody::handler);
        try { return future.get(5, java.util.concurrent.TimeUnit.SECONDS); }
        finally { future.cancel(true); }
    }

    /** Sends only the fixed code message with mandatory validated STARTTLS.
     * @param email recipient
     * @param code ephemeral code
     * @return successful send
     */
    @Override
    public boolean mail(String email, String code) {
        try {
            Session session = Session.getInstance(properties());
            MimeMessage message = new MimeMessage(session);
            message.setFrom(new InternetAddress(config.sender()));
            message.setRecipient(Message.RecipientType.TO, new InternetAddress(email));
            message.setSubject("AI access request verification", "UTF-8");
            message.setText("Verification code: " + code + "\nExpires in 10 minutes.\nSite: " + config.hostname(), "UTF-8");
            try (Transport transport = session.getTransport("smtp")) {
                transport.connect(config.smtpHost(), config.smtpPort(), config.smtpUsername(), config.smtpPassword());
                if (!authenticated(transport)) return false;
                transport.sendMessage(message, message.getAllRecipients());
            }
            return true;
        } catch (Exception failure) { return false; }
    }
    /** Requires the pinned provider to have negotiated TLS and authenticated successfully.
     * @param transport connected transport
     * @return positive authenticated TLS state
     */
    static boolean authenticated(Transport transport) {
        return transport instanceof org.eclipse.angus.mail.smtp.SMTPTransport smtp
                && smtp.isSSL() && smtp.supportsExtension("AUTH") && smtp.getLastReturnCode() == 235;
    }

    /** Constructs bounded authenticated TLS-only SMTP properties.
     * @return fresh transport properties
     */
    private Properties properties() {
        Properties result = new Properties();
        result.setProperty("mail.smtp.auth", "true");
        result.setProperty("mail.smtp.starttls.enable", "true");
        result.setProperty("mail.smtp.starttls.required", "true");
        result.setProperty("mail.smtp.ssl.checkserveridentity", "true");
        result.setProperty("mail.smtp.connectiontimeout", "5000");
        result.setProperty("mail.smtp.timeout", "5000");
        result.setProperty("mail.smtp.writetimeout", "5000");
        return result;
    }
}
