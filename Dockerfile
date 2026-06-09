FROM node:20-slim AS node

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
COPY frontend/ /frontend
WORKDIR /frontend

FROM node AS frontend
RUN pnpm install --frozen-lockfile
RUN pnpm run build

FROM eclipse-temurin:21-jdk-jammy AS backend
WORKDIR /app

COPY backend/.mvn/ .mvn/
COPY backend/mvnw ./
COPY backend/pom.xml ./
COPY backend/src ./src/
COPY --from=frontend /frontend/dist/ ./src/main/resources/static/
RUN chmod +x mvnw && ./mvnw package -Dmaven.test.skip

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=backend /app/target/*.jar app.jar
RUN addgroup --system spring && adduser --system --ingroup spring --home /home/spring spring
USER spring:spring
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
