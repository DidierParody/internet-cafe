package org.internetcafe.desktop.screens;

import com.google.zxing.common.BitMatrix;
import javafx.animation.KeyFrame;
import javafx.animation.Timeline;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.image.ImageView;
import javafx.scene.image.PixelWriter;
import javafx.scene.image.WritableImage;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.util.Duration;
import org.internetcafe.desktop.qr.QrCountdown;
import org.internetcafe.desktop.qr.QrRotationService;
import org.internetcafe.desktop.services.ApiClient;

public class QrScreen {
  private final VBox root;
  private final ImageView qrView;
  private final Label countdownLabel;
  private Runnable onBack;
  private QrRotationService rotationService;
  private Timeline countdownTimeline;
  private QrCountdown countdown;

  public QrScreen() {
    Label title = new Label("QR de acceso");
    title.setStyle("-fx-font-size: 26px; -fx-font-weight: 700;");

    qrView = new ImageView();
    qrView.setFitWidth(240);
    qrView.setFitHeight(240);
    qrView.setPreserveRatio(true);

    countdownLabel = new Label("");
    countdownLabel.setStyle("-fx-font-size: 16px;");

    Button backButton = new Button("Volver");

    backButton.setOnAction(
        event -> {
          stopRotation();
          if (onBack != null) {
            onBack.run();
          }
        });

    root = new VBox(18);
    root.setPadding(new Insets(32));
    root.setAlignment(Pos.CENTER);
    root.getChildren().addAll(title, qrView, countdownLabel, backButton);
  }

  public void startRotation(ApiClient apiClient, String machineCode) {
    stopRotation();
    rotationService =
        new QrRotationService(() -> apiClient.createChallenge(machineCode), this::onChallengeReady);
    rotationService.start();
  }

  public void stopRotation() {
    if (countdownTimeline != null) {
      countdownTimeline.stop();
      countdownTimeline = null;
    }
    countdown = null;
    if (rotationService != null) {
      rotationService.stop();
      rotationService = null;
    }
  }

  public VBox getRoot() {
    return root;
  }

  public void setOnBack(Runnable onBack) {
    this.onBack = onBack;
  }

  private void onChallengeReady(BitMatrix qr, QrCountdown nextCountdown) {
    Runnable update =
        () -> {
          qrView.setImage(toImage(qr));
          countdown = nextCountdown;
          updateCountdownLabel();
          startCountdownTicks();
        };
    if (Platform.isFxApplicationThread()) {
      update.run();
    } else {
      Platform.runLater(update);
    }
  }

  private void startCountdownTicks() {
    if (countdownTimeline != null) {
      countdownTimeline.stop();
    }
    countdownTimeline =
        new Timeline(new KeyFrame(Duration.seconds(1), event -> updateCountdownLabel()));
    countdownTimeline.setCycleCount(Timeline.INDEFINITE);
    countdownTimeline.play();
  }

  private void updateCountdownLabel() {
    if (countdown == null) {
      countdownLabel.setText("");
      return;
    }
    countdownLabel.setText(countdown.remainingSeconds() + " s");
  }

  private static WritableImage toImage(BitMatrix matrix) {
    int width = matrix.getWidth();
    int height = matrix.getHeight();
    WritableImage image = new WritableImage(width, height);
    PixelWriter pixels = image.getPixelWriter();
    for (int y = 0; y < height; y++) {
      for (int x = 0; x < width; x++) {
        pixels.setColor(x, y, matrix.get(x, y) ? Color.BLACK : Color.WHITE);
      }
    }
    return image;
  }
}
