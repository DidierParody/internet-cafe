package org.internetcafe.desktop;

public final class AppConfig {
    private static final String DEFAULT_API_BASE_URL = "http://localhost:8000/api";

    private AppConfig() {}

    public static String getApiBaseUrl() {
        return System.getProperty("api.base.url", DEFAULT_API_BASE_URL);
    }
}
