# Minecraft Plugin Template (Paper)

A starter template for building Minecraft plugins targeting the [Paper](https://papermc.io/) server using Gradle.

## Features

- **Paper API 1.21.4** — configured as a `compileOnly` dependency
- **Shadow JAR** — produces a single fat JAR via [Gradle Shadow](https://github.com/GradleUp/shadow)
- **Java 21 toolchain** — enforced via Gradle, no manual JDK management
- **Version injection** — `plugin.yml` version is set automatically from `build.gradle`
- **Local server support** — place `paper.jar` in `run/` to enable `copyToServer` and IDE run configs
- **GitHub Actions CI** — builds on push/PR, creates GitHub Releases on `v*` tags

## Requirements

- Java 21+
- Gradle 9.2+ (included via wrapper)

## Quick Start

1. Click **Use this template** on GitHub (or clone the repo).
2. Update the placeholder names (see [Customization](#customization) below).
3. Build the plugin:

```bash
./gradlew build
```

On Windows PowerShell:

```powershell
.\gradlew.bat build
```

The plugin JAR will be in `build/libs/`.

## Local Server Testing

To automatically copy the built JAR into a local Paper server:

1. Place your `paper.jar` in the `run/` directory (or pass `-Pmc_server_jar=/path/to/paper.jar`).
2. Run:

```bash
./gradlew copyToServer
```

The build will also generate IDE run configurations (IntelliJ / VS Code) when the server JAR is detected.

## Gradle Tasks

| Task | Description |
|------|-------------|
| `build` | Compile + Shadow JAR |
| `shadowJar` | Produce the shaded plugin JAR |
| `test` | Run unit tests |
| `copyToServer` | Copy the JAR to `run/plugins/` (requires server JAR) |
| `generateVSCodeLaunch` | Generate `.vscode/launch.json` for the Paper server |
| `copyDependencies` | Copy compile classpath to `build/dependencies/` |

## Customization

Before using in production, update:

- `group` and `version` in `build.gradle`
- `rootProject.name` in `settings.gradle`
- Package path under `src/main/java/`
- `name`, `main`, `author`, and `description` in `src/main/resources/plugin.yml`

## CI / Releases

The included GitHub Actions workflow (`.github/workflows/build.yml`):

- Builds and tests on pushes to `main`/`develop` and on pull requests
- Creates a GitHub Release with the plugin JAR when you push a `v*` tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```
