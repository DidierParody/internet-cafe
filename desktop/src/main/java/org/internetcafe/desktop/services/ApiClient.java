package org.internetcafe.desktop.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.internetcafe.desktop.AppConfig;

public class ApiClient {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private final HttpClient httpClient;

    public ApiClient() {
        this.httpClient =
                HttpClient.newBuilder()
                        .connectTimeout(Duration.ofSeconds(10))
                        .build();
    }

    public String getHealth() {
        try {
            HttpRequest request =
                    HttpRequest.newBuilder()
                            .uri(URI.create(AppConfig.getApiBaseUrl() + "/healthz"))
                            .timeout(Duration.ofSeconds(15))
                            .GET()
                            .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            return response.body();
        } catch (Exception e) {
            return "{\"status\":\"offline\"}";
        }
    }

    public ObjectMapper getObjectMapper() {
        return OBJECT_MAPPER;
    }
}
