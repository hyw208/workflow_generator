FROM camunda/camunda-bpm-platform:run-7.20.0

USER root

# Download Camunda Connect HTTP connector JARs
RUN mkdir -p /camunda/lib && \
    curl -L -o /camunda/lib/camunda-connect-core-1.5.0.jar https://repo1.maven.org/maven2/org/camunda/connect/camunda-connect-core/1.5.0/camunda-connect-core-1.5.0.jar && \
    curl -L -o /camunda/lib/camunda-connect-http-client-1.5.0.jar https://repo1.maven.org/maven2/org/camunda/connect/camunda-connect-http-client/1.5.0/camunda-connect-http-client-1.5.0.jar && \
    curl -L -o /camunda/lib/camunda-engine-plugin-connect-7.20.0.jar https://repo1.maven.org/maven2/org/camunda/bpm/camunda-engine-plugin-connect/7.20.0/camunda-engine-plugin-connect-7.20.0.jar

USER camunda
