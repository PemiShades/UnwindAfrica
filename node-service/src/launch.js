import "dotenv/config";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const djangoDir = path.resolve(repoRoot, process.env.DJANGO_WORKDIR || ".");
const python = process.env.PYTHON_BIN || (process.platform === "win32" ? "python" : "python3");
const port = process.env.DJANGO_PORT || "8000";
const djangoArgs = process.platform === "win32"
  ? ["manage.py", "runserver", `127.0.0.1:${port}`, "--noreload"]
  : ["-m", "gunicorn", "config.wsgi:application", "--bind", `127.0.0.1:${port}`, "--workers", process.env.WEB_CONCURRENCY || "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"];

const child = spawn(python, djangoArgs, {
  cwd: djangoDir,
  env: {
    ...process.env,
    ...(process.platform === "win32" && !process.env.DEBUG ? { DEBUG: "True" } : {}),
    PYTHONUNBUFFERED: "1",
    PORT: port,
  },
  stdio: "inherit",
});

child.on("error", (error) => {
  console.error("Could not start Django:", error);
  process.exit(1);
});
child.on("exit", (code, signal) => {
  console.error(`Django/Gunicorn exited (code=${code}, signal=${signal}); stopping gateway.`);
  process.exit(code || 1);
});

async function waitForDjango() {
  const healthUrl = `http://127.0.0.1:${port}/healthz`;
  const deadline = Date.now() + Number(process.env.DJANGO_STARTUP_TIMEOUT_MS || 90000);
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error("Django exited before becoming healthy.");
    try {
      const response = await fetch(healthUrl, { signal: AbortSignal.timeout(1500) });
      if (response.ok) return;
    } catch { /* Django is still starting. */ }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("Django did not become healthy before the startup timeout.");
}

try {
  await waitForDjango();
  console.log("Django is healthy; starting the shared website and app gateway.");
  await import("./server.js");
} catch (error) {
  console.error(error);
  child.kill("SIGTERM");
  process.exit(1);
}

function stop(signal) {
  child.kill(signal);
  setTimeout(() => process.exit(0), 5000).unref();
}
process.on("SIGTERM", () => stop("SIGTERM"));
process.on("SIGINT", () => stop("SIGINT"));
