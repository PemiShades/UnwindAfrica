import "dotenv/config";
import express from "express";
import helmet from "helmet";
import { Readable } from "node:stream";

const app = express();
const port = Number(process.env.PORT || 4100);
const djangoOrigin = (process.env.DJANGO_INTERNAL_ORIGIN || "http://127.0.0.1:8000").replace(/\/$/, "");

app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(helmet({ contentSecurityPolicy: false, crossOriginResourcePolicy: { policy: "cross-origin" } }));

const hopByHop = new Set(["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade", "host"]);

app.get("/health", async (_request, response) => {
  try {
    const upstream = await fetch(`${djangoOrigin}/healthz`, { signal: AbortSignal.timeout(4000) });
    if (!upstream.ok) return response.status(503).json({ status: "unavailable", django: upstream.status });
    return response.json({ service: "unwind-africa", status: "ok", django: "ok" });
  } catch {
    return response.status(503).json({ service: "unwind-africa", status: "unavailable", django: "unavailable" });
  }
});

// The same public origin serves Django pages and the mobile app API. Stream the
// original request so forms, uploads, cookies, and payment callbacks are intact.
app.use(async (request, response) => {
  const target = `${djangoOrigin}${request.originalUrl}`;
  const headers = new Headers();
  for (const [name, value] of Object.entries(request.headers)) {
    if (value == null || hopByHop.has(name.toLowerCase())) continue;
    headers.set(name, Array.isArray(value) ? value.join(", ") : value);
  }
  headers.set("x-forwarded-host", request.get("host") || "");
  headers.set("x-forwarded-proto", request.get("x-forwarded-proto") || request.protocol);
  headers.set("x-forwarded-for", request.ip || "");

  try {
    const hasBody = !["GET", "HEAD"].includes(request.method);
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request : undefined,
      ...(hasBody ? { duplex: "half" } : {}),
      redirect: "manual",
      signal: AbortSignal.timeout(Number(process.env.PROXY_TIMEOUT_MS || 120000)),
    });
    response.status(upstream.status);
    upstream.headers.forEach((value, name) => {
      if (!hopByHop.has(name.toLowerCase()) && !["content-encoding", "content-length", "set-cookie"].includes(name.toLowerCase())) response.setHeader(name, value);
    });
    const cookies = upstream.headers.getSetCookie?.() || [];
    if (cookies.length) response.setHeader("set-cookie", cookies);
    if (!upstream.body) return response.end();
    Readable.fromWeb(upstream.body).pipe(response);
  } catch (error) {
    if (response.headersSent) return response.destroy(error);
    response.status(502).type("text/plain").send("Unwind Africa is temporarily unavailable. Please try again shortly.");
  }
});

app.listen(port, "0.0.0.0", () => console.log(`Unwind Africa gateway listening on ${port}`));
